// Stable byte routing from the field and offset known before the next byte.
// All offsets and counts are bounded by the length of one input block.
#include <algorithm>
#include <array>
#include <cstdint>
#include <vector>

namespace {
struct State {
  unsigned field = 0, column = 0;
  void observe(uint8_t byte) {
    if (byte == '\n') {
      field = column = 0;
    } else if (byte == ',') {
      field = std::min(7U, field + 1);
      column = 0;
    } else {
      column = std::min(15U, column + 1);
    }
  }
  unsigned lane(unsigned fields, unsigned columns) const {
    return (fields == 1 ? 0 : field * columns) + (columns == 1 ? 0 : column);
  }
};
} // namespace

extern "C" int field_lanes(const uint8_t *input, uint8_t *output, uint32_t size,
                           uint32_t *lengths, unsigned fields, unsigned columns,
                           int inverse) {
  if ((fields != 1 && fields != 8) || (columns != 1 && columns != 16))
    return 1;
  const unsigned count = fields * columns;
  State state;
  if (!inverse) {
    std::fill(lengths, lengths + count, 0);
    for (uint32_t i = 0; i < size; ++i) {
      ++lengths[state.lane(fields, columns)];
      state.observe(input[i]);
    }
  }
  std::array<uint32_t, 128> cursor{}, end{};
  uint32_t total = 0;
  for (unsigned lane = 0; lane < count; ++lane) {
    if (lengths[lane] > size - total)
      return 1;
    cursor[lane] = total;
    total += lengths[lane];
    end[lane] = total;
  }
  if (total != size)
    return 1;
  state = {};
  for (uint32_t i = 0; i < size; ++i) {
    const unsigned lane = state.lane(fields, columns);
    if (cursor[lane] == end[lane])
      return 1;
    const uint32_t index = cursor[lane]++;
    const uint8_t byte = inverse ? input[index] : input[i];
    output[inverse ? i : index] = byte;
    state.observe(byte);
  }
  return 0;
}

// Front-code consecutive tokens in each field stream. Keep the delimiter in
// the suffix so the receiver can discover both token boundaries and lane order.

extern "C" int64_t front_fields(const uint8_t *input, uint32_t size,
                                uint8_t *output, uint32_t capacity,
                                uint32_t *lengths, unsigned lanes,
                                int inverse) {
  if (lanes != 1 && lanes != 8)
    return -1;
  std::array<uint32_t, 8> previous{}, previous_length{}, cursor{}, end{};
  std::array<std::vector<uint8_t>, 8> streams;
  unsigned lane = 0;
  uint32_t pos = 0;
  if (!inverse) {
    while (pos < size) {
      const uint32_t start = pos;
      while (pos < size && input[pos] != ',' && input[pos] != '\n')
        ++pos;
      const uint32_t width = pos - start;
      uint32_t prefix = 0;
      while (prefix < std::min(width, previous_length[lane]) &&
             input[start + prefix] == input[previous[lane] + prefix])
        ++prefix;
      auto &stream = streams[lane];
      uint32_t value = prefix;
      while (value >= 128) {
        stream.push_back(static_cast<uint8_t>((value & 127) | 128));
        value >>= 7;
      }
      stream.push_back(static_cast<uint8_t>(value));
      stream.insert(stream.end(), input + start + prefix, input + pos);
      previous[lane] = start;
      previous_length[lane] = width;
      if (pos < size) {
        const uint8_t sep = input[pos++];
        stream.push_back(sep);
        lane = sep == '\n' ? 0 : std::min(lanes - 1, lane + 1);
      }
    }
    uint32_t written = 0;
    for (unsigned i = 0; i < lanes; ++i) {
      if (streams[i].size() > capacity - written)
        return -1;
      lengths[i] = static_cast<uint32_t>(streams[i].size());
      std::copy(streams[i].begin(), streams[i].end(), output + written);
      written += lengths[i];
    }
    return written;
  }

  uint32_t total = 0;
  for (unsigned i = 0; i < lanes; ++i) {
    if (lengths[i] > size - total)
      return -1;
    cursor[i] = total;
    total += lengths[i];
    end[i] = total;
  }
  if (total != size)
    return -1;
  while (pos < capacity) {
    const uint32_t start = pos;
    uint32_t prefix = 0;
    for (unsigned shift = 0;; shift += 7) {
      if (cursor[lane] == end[lane] || shift > 21)
        return -1;
      const uint8_t byte = input[cursor[lane]++];
      prefix |= static_cast<uint32_t>(byte & 127) << shift;
      if (!(byte & 128))
        break;
    }
    if (prefix > previous_length[lane] || prefix > capacity - pos)
      return -1;
    std::copy_n(output + previous[lane], prefix, output + pos);
    pos += prefix;
    while (cursor[lane] < end[lane] && input[cursor[lane]] != ',' &&
           input[cursor[lane]] != '\n') {
      if (pos == capacity)
        return -1;
      output[pos++] = input[cursor[lane]++];
    }
    previous[lane] = start;
    previous_length[lane] = pos - start;
    if (cursor[lane] < end[lane]) {
      if (pos == capacity)
        return -1;
      const uint8_t sep = input[cursor[lane]++];
      output[pos++] = sep;
      lane = sep == '\n' ? 0 : std::min(lanes - 1, lane + 1);
    } else if (pos != capacity) {
      return -1;
    }
  }
  return cursor == end ? static_cast<int64_t>(pos) : -1;
}
