#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

// All proposals depend exclusively on bytes the decoder has already produced.
class PatternPredictor {
public:
    enum Model { Period = 1, Ramp = 2, Xorshift = 4, Numeric = 8 };

    explicit PatternPredictor(unsigned models) : models_(models), numbers_(models & Numeric ? 1u << 17 : 0) {
        for (auto& weights : weights_) weights.fill(0.05f);
    }

    void start_byte(const uint8_t* bytes, size_t position) {
        prediction_ = -1;
        int best = activation_score_ - 1;
        if (period_) offer(bytes[position - period_], period_score_, 0, best);
        if (models_ & Ramp) offer(ramp_next_, ramp_score_, 1, best);
        if (models_ & Xorshift) {
            for (size_t end = 0; end < phases_.size(); ++end) {
                const Phase& phase = phases_[end];
                const unsigned shift = 8 * ((end + 4 - (position & 3)) & 3);
                offer(static_cast<uint8_t>(phase.next >> shift), phase.score, 2, best);
            }
        }
        if ((models_ & Numeric) && position >= 8) {
            if (!number_width_) predict_number();
            if (number_width_ < predicted_width_)
                offer(number_digits_[predicted_width_ - 1 - number_width_], number_score_, 3, best);
        }
        if (prediction_ >= 0) {
            const int bucket = std::min(3, (best - activation_score_) / 16);
            weight_ = &weights_[family_][bucket];
            posterior_ = *weight_;
        }
    }

    float mix(float base, int bit_position) {
        if (prediction_ < 0) return base;
        const bool expected_bit = (prediction_ >> bit_position) & 1;
        expert_ = expected_bit ? 0.995f : 0.005f;
        mixed_ = base + posterior_ * (expert_ - base);
        return mixed_;
    }

    void observe_bit(int bit, int bit_position) {
        if (prediction_ < 0) return;
        const float expert_truth = bit ? expert_ : 1.0f - expert_;
        const float mixed_truth = bit ? mixed_ : 1.0f - mixed_;
        posterior_ = std::min(1.0f, posterior_ * expert_truth / mixed_truth);
        if (bit_position == 0 || bit != ((prediction_ >> bit_position) & 1)) {
            *weight_ = std::clamp(*weight_ + 0.15f * (posterior_ - *weight_), 0.005f, 0.995f);
            prediction_ = -1;
        }
    }

    void observe_byte(const uint8_t* bytes, size_t position) {
        const uint8_t value = bytes[position];
        if (models_ & Period) {
            period_ = 0;
            period_score_ = activation_score_ - 1;
            for (size_t index = 0; index < periods_.size() && position >= periods_[index]; ++index) {
                const size_t period = periods_[index];
                int& score = period_scores_[index];
                update(score, value == bytes[position - period]);
                if (score > period_score_) {
                    period_ = period;
                    period_score_ = score;
                }
            }
        }
        if ((models_ & Ramp) && position > 0) observe_ramp(value, bytes[position - 1]);
        if (models_ & Xorshift) observe_xorshift(value, position);
        if (models_ & Numeric) observe_number(value);
    }

private:
    struct Phase {
        uint32_t next = 0;
        int score = 0;
    };

    struct Number {
        uint64_t prefix = 0;
        int previous = 0;
        int step = 0;
        unsigned width = 0;
        unsigned samples = 0;
        int repeat_score = 0;
        int linear_score = 0;
    };

    static void update(int& score, bool hit) {
        if (hit) score += (256 - score + 7) >> 3;
        else score -= (score + 3) >> 2;
    }

    static uint32_t xorshift(uint32_t word) {
        word ^= word << 13;
        word ^= word >> 17;
        return word ^ (word << 5);
    }

    void offer(uint8_t value, int score, int family, int& best) {
        if (score > best) {
            best = score;
            family_ = family;
            prediction_ = value;
        }
    }

    void observe_ramp(uint8_t value, uint8_t previous) {
        const uint8_t step = value - previous;
        if (ramp_step_ && ramp_score_ > 0) {
            const bool hit = value == ramp_next_;
            update(ramp_score_, hit);
            if (hit || ramp_score_ >= 96) {
                ramp_next_ += ramp_step_;
                return;
            }
        }
        ramp_score_ = step && step == ramp_step_ ? ramp_score_ : 0;
        ramp_step_ = step;
        if (step) update(ramp_score_, true);
        ramp_next_ = value + ramp_step_;
    }

    void observe_xorshift(uint8_t value, size_t position) {
        recent_ = (recent_ << 8) | value;
        if (position < 3) return;
        Phase& phase = phases_[position & 3];
        const bool hit = phase.next != 0 && recent_ == phase.next;
        update(phase.score, hit);
        // A sparse error does not reset a well-established sequence.
        if (!hit && phase.score < 96) phase.next = recent_;
        phase.next = xorshift(phase.next);
    }

    Number& number_at(uint64_t prefix) {
        return numbers_[((prefix ^ (prefix >> 29)) * 0x9e3779b97f4a7c15ull) >> 47];
    }

    void predict_number() {
        predicted_width_ = 0;
        const Number& model = number_at(number_history_);
        if (!model.width || model.prefix != number_history_) return;
        number_score_ = std::max(model.repeat_score, model.linear_score);
        if (number_score_ < activation_score_) return;
        const bool linear = model.linear_score > model.repeat_score;
        int value = model.previous + (linear ? model.step : 0);
        if (value < 0 || value > 999999999) return;
        do {
            number_digits_[predicted_width_++] = static_cast<uint8_t>('0' + value % 10);
            value /= 10;
        } while (value);
        while (predicted_width_ < model.width) number_digits_[predicted_width_++] = '0';
    }

    void observe_number(uint8_t byte) {
        const bool digit = byte >= '0' && byte <= '9';
        if (digit) {
            if (!number_width_) number_prefix_ = number_history_;
            if (number_width_ < number_digits_.size()) number_value_ = 10 * number_value_ + byte - '0';
            number_width_ = std::min(10u, number_width_ + 1);
        } else if (number_width_) {
            if (number_width_ <= number_digits_.size()) {
                Number& model = number_at(number_prefix_);
                if (model.prefix != number_prefix_) {
                    model = Number{};
                    model.prefix = number_prefix_;
                }
                if (model.samples) update(model.repeat_score, model.previous == number_value_ && model.width == number_width_);
                if (model.samples >= 2) update(model.linear_score, model.previous + model.step == number_value_);
                model.step = number_value_ - model.previous;
                model.previous = number_value_;
                model.width = number_width_;
                model.samples = std::min(2u, model.samples + 1);
            }
            number_value_ = 0;
            number_width_ = 0;
            predicted_width_ = 0;
        }
        number_history_ = (number_history_ << 8) | (digit ? '0' : byte);
    }

    static constexpr int activation_score_ = 192;
    inline static constexpr std::array<size_t, 29> periods_ = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
        24, 32, 48, 64, 96, 128, 192, 256,
        384, 512, 768, 1024, 2048,
    };
    const unsigned models_;
    std::array<int, periods_.size()> period_scores_{};
    size_t period_ = 0;
    int period_score_ = 0;
    int ramp_score_ = 0;
    uint8_t ramp_step_ = 0, ramp_next_ = 0;
    uint32_t recent_ = 0;
    std::array<Phase, 4> phases_{};
    std::vector<Number> numbers_;
    std::array<uint8_t, 9> number_digits_{};
    uint64_t number_prefix_ = 0, number_history_ = 0;
    unsigned number_width_ = 0, predicted_width_ = 0;
    int number_value_ = 0, number_score_ = 0;
    std::array<std::array<float, 4>, 4> weights_{};
    int prediction_ = -1, family_ = 0;
    float* weight_ = nullptr;
    float posterior_ = 0, expert_ = 0, mixed_ = 0;
};
