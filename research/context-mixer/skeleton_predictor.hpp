#pragma once

#include <algorithm>
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <vector>

// Follow a past string after folding decimal digits or ASCII case. The
// arithmetic coder still encodes the actual bytes, including every edit.
class SkeletonPredictor {
public:
    explicit SkeletonPredictor(unsigned modes) : modes_(modes), table_(modes ? kSlots : 0) {
        weights_.fill(0.08f);
    }

    void start_byte(const uint8_t* bytes, size_t position, int exact_prediction) {
        active_ = false;
        if (position < kSuffix) return;

        auto& entry = table_[((history_ * 0x9e3779b97f4a7c15ull) ^ (history_ >> 23)) >> (64 - kTableBits)];
        if (!length_) {
            for (uint32_t reference : entry) {
                if (reference < kSuffix || reference >= position) continue;
                unsigned length = 0;
                bool edited = false;
                const size_t maximum = std::min({position, size_t(reference), size_t(kMaxBack)});
                while (length < maximum) {
                    const uint8_t here = bytes[position - length - 1];
                    const uint8_t there = bytes[reference - length - 1];
                    if (shape(here) != shape(there)) break;
                    edited |= here != there;
                    ++length;
                }
                if (length >= kSuffix && length > length_) {
                    reference_ = reference;
                    length_ = length;
                    edited_ = edited;
                    numeric_ = is_digit(bytes[reference - 1]) && is_digit(bytes[position - 1]);
                    extra_digits_ = 0;
                }
            }
        }
        entry[1] = entry[0];
        entry[0] = static_cast<uint32_t>(position);

        if (!length_ || !edited_) return;
        const uint8_t next = bytes[reference_];
        if (next == exact_prediction) return;

        prediction_ = next;
        const unsigned kind = is_digit(next) && (modes_ & 1) ? 1
                           : is_letter(next) && (modes_ & 2) ? 2 : 0;
        kind_ = kind;
        const unsigned bucket = std::min(3u, static_cast<unsigned>(std::bit_width(length_)) - 4);
        const unsigned group = !kind && numeric_ && (modes_ & 4) ? 3 : kind;
        weight_ = &weights_[group * 4 + bucket];
        posterior_ = *weight_;
        active_ = true;
    }

    float mix(float base, int bit_position, int prefix) {
        if (!active_) return base;
        const unsigned half = 1u << bit_position;
        const unsigned mask = ~(2 * half - 1) & 255;
        const unsigned observed = static_cast<unsigned>(prefix << (bit_position + 1)) & 255;
        bool zero = false;
        bool one = false;
        auto offer = [&](unsigned value) {
            if ((value & mask) != observed) return;
            if (value & half) one = true;
            else zero = true;
        };

        if (kind_ == 1) {
            // A contiguous ASCII digit interval can intersect each child of the bit tree.
            zero = observed <= '9' && observed + half - 1 >= '0';
            one = observed + half <= '9' && observed + 2 * half - 1 >= '0';
        } else {
            offer(prediction_);
            if (kind_ == 2) offer(prediction_ ^ 32);
        }
        expert_ = zero == one ? base : one ? 0.995f : 0.005f;
        compatible_ = (zero ? 1 : 0) | (one ? 2 : 0);
        mixed_ = base + posterior_ * (expert_ - base);
        return mixed_;
    }

    void observe_bit(int bit, int bit_position) {
        if (!active_) return;
        const float expert_truth = bit ? expert_ : 1.0f - expert_;
        const float mixed_truth = bit ? mixed_ : 1.0f - mixed_;
        posterior_ = std::min(1.0f, posterior_ * expert_truth / mixed_truth);
        if (bit_position == 0 || !(compatible_ & (1 << bit))) {
            *weight_ = std::clamp(*weight_ + 0.1f * (posterior_ - *weight_), 0.001f, 0.995f);
            active_ = false;
        }
    }

    void observe_byte(const uint8_t* bytes, size_t position) {
        const uint8_t value = bytes[position];
        const uint8_t folded = shape(value);
        history_ = (history_ << 8) | folded;
        if (!length_) return;

        const uint8_t reference = bytes[reference_];
        if (shape(reference) == folded) {
            edited_ |= reference != value;
            numeric_ = is_digit(reference) && is_digit(value);
            extra_digits_ = 0;
            ++reference_;
            ++length_;
            return;
        }

        if ((modes_ & 5) == 5 && numeric_) {
            if (is_digit(value) && !is_digit(reference) && extra_digits_ < kMaxExtraDigits) {
                // The current field is longer. Keep the earlier delimiter pending.
                ++extra_digits_;
                edited_ = true;
                return;
            }
            if (!is_digit(value) && is_digit(reference)) {
                // Scan only bytes both encoder and decoder already know.
                const size_t limit = std::min(position, reference_ + kMaxExtraDigits + 1);
                size_t delimiter = reference_ + 1;
                while (delimiter < limit && is_digit(bytes[delimiter])) ++delimiter;
                if (delimiter < limit && shape(bytes[delimiter]) == folded) {
                    reference_ = delimiter + 1;
                    ++length_;
                    numeric_ = false;
                    extra_digits_ = 0;
                    edited_ = true;
                    return;
                }
            }
        }
        length_ = 0;
        edited_ = false;
        numeric_ = false;
        extra_digits_ = 0;
    }

private:
    static bool is_digit(unsigned value) { return value >= '0' && value <= '9'; }

    static bool is_letter(unsigned value) {
        return (value | 32) >= 'a' && (value | 32) <= 'z';
    }

    uint8_t shape(uint8_t value) const {
        if ((modes_ & 1) && is_digit(value)) return '0';
        if ((modes_ & 2) && is_letter(value)) return value | 32;
        return value;
    }

    static constexpr unsigned kSuffix = 8;
    static constexpr unsigned kMaxBack = 64;
    static constexpr unsigned kMaxExtraDigits = 4;
    static constexpr unsigned kTableBits = 18;
    static constexpr size_t kSlots = 1u << kTableBits;

    unsigned modes_;
    std::vector<std::array<uint32_t, 2>> table_;
    std::array<float, 16> weights_{};
    uint64_t history_ = 0;
    size_t reference_ = 0;
    unsigned length_ = 0;
    bool edited_ = false;
    bool numeric_ = false;
    unsigned extra_digits_ = 0;
    bool active_ = false;
    unsigned prediction_ = 0;
    unsigned kind_ = 0;
    int compatible_ = 0;
    float* weight_ = nullptr;
    float posterior_ = 0;
    float expert_ = 0;
    float mixed_ = 0;
};
