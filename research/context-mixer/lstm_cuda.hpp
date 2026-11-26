#pragma once

#include <cublas_v2.h>
#include <cuda_runtime_api.h>
#include <stdexcept>
#include <string>
#include <vector>

inline void check_cuda(cudaError_t status) {
    if (status != cudaSuccess) throw std::runtime_error(cudaGetErrorString(status));
}

inline void check_cublas(cublasStatus_t status) {
    if (status != CUBLAS_STATUS_SUCCESS) {
        throw std::runtime_error("cuBLAS failed with status " + std::to_string(status));
    }
}

class CudaFloatBuffer {
public:
    explicit CudaFloatBuffer(size_t count) : count_(count) {
        check_cuda(cudaMalloc(reinterpret_cast<void**>(&data_), count_ * sizeof(float)));
    }

    CudaFloatBuffer(const CudaFloatBuffer&) = delete;
    CudaFloatBuffer& operator=(const CudaFloatBuffer&) = delete;
    ~CudaFloatBuffer() { cudaFree(data_); }

    float* data() const { return data_; }

    void upload(const std::vector<float>& source) {
        check_cuda(cudaMemcpy(data_, source.data(), count_ * sizeof(float), cudaMemcpyHostToDevice));
    }

    void download(std::vector<float>& destination) const {
        check_cuda(cudaMemcpy(destination.data(), data_, count_ * sizeof(float), cudaMemcpyDeviceToHost));
    }

private:
    size_t count_;
    float* data_ = nullptr;
};

class CudaLstmGradients {
public:
    CudaLstmGradients(int cells, int window)
        : cells_(cells), window_(window), output_error_(size_t(window) * 256),
          output_weights_(size_t(256) * cells), hidden_(size_t(window) * cells),
          hidden_error_(size_t(window) * cells), output_gradient_(size_t(256) * cells),
          gate_error_(size_t(window) * 4 * cells), previous_hidden_(size_t(window) * cells),
          recurrent_gradient_(size_t(4) * cells * cells) {
        check_cublas(cublasCreate(&handle_));
        const cublasStatus_t status = cublasSetMathMode(handle_, CUBLAS_PEDANTIC_MATH);
        if (status != CUBLAS_STATUS_SUCCESS) {
            cublasDestroy(handle_);
            check_cublas(status);
        }
    }

    CudaLstmGradients(const CudaLstmGradients&) = delete;
    CudaLstmGradients& operator=(const CudaLstmGradients&) = delete;
    ~CudaLstmGradients() { cublasDestroy(handle_); }

    void backprop_output(const std::vector<float>& errors, const std::vector<float>& weights,
                         const std::vector<float>& hidden, std::vector<float>& hidden_errors) {
        output_error_.upload(errors);
        output_weights_.upload(weights);
        hidden_.upload(hidden);

        // cuBLAS sees each row-major matrix as its column-major transpose.
        multiply(CUBLAS_OP_N, cells_, window_, 256, output_weights_, cells_,
                 output_error_, 256, hidden_error_);
        hidden_error_.download(hidden_errors);
        multiply(CUBLAS_OP_T, cells_, 256, window_, hidden_, cells_,
                 output_error_, 256, output_gradient_);
    }

    void backprop_recurrent(const std::vector<float>& errors, const std::vector<float>& previous_hidden,
                            std::vector<float>& recurrent_gradient, std::vector<float>& output_gradient) {
        gate_error_.upload(errors);
        previous_hidden_.upload(previous_hidden);
        multiply(CUBLAS_OP_T, cells_, 4 * cells_, window_, previous_hidden_, cells_,
                 gate_error_, 4 * cells_, recurrent_gradient_);
        recurrent_gradient_.download(recurrent_gradient);
        output_gradient_.download(output_gradient);
    }

private:
    void multiply(cublasOperation_t transpose_b, int m, int n, int k,
                  const CudaFloatBuffer& a, int lda, const CudaFloatBuffer& b, int ldb,
                  CudaFloatBuffer& out) {
        constexpr float one = 1.0f;
        constexpr float zero = 0.0f;
        check_cublas(cublasSgemm(handle_, CUBLAS_OP_N, transpose_b, m, n, k,
                                &one, a.data(), lda, b.data(), ldb, &zero, out.data(), m));
    }

    int cells_;
    int window_;
    cublasHandle_t handle_ = nullptr;
    CudaFloatBuffer output_error_, output_weights_, hidden_, hidden_error_, output_gradient_;
    CudaFloatBuffer gate_error_, previous_hidden_, recurrent_gradient_;
};
