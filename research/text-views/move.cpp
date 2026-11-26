// The move-to-front transform from lab/arena/view.cpp, exposed for byte
// buffers.
#include <cstddef>
#include <cstdint>
#include <cstring>

extern "C" void move_front(uint8_t *data, size_t length, int inverse) {
  uint8_t order[256];
  for (unsigned i = 0; i < 256; ++i)
    order[i] = static_cast<uint8_t>(i);
  for (size_t i = 0; i < length; ++i) {
    unsigned rank = 0;
    uint8_t symbol = data[i];
    if (inverse) {
      rank = symbol;
      symbol = order[rank];
      data[i] = symbol;
    } else {
      while (order[rank] != symbol)
        ++rank;
      data[i] = static_cast<uint8_t>(rank);
    }
    std::memmove(order + 1, order, rank);
    order[0] = symbol;
  }
}
