#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <gmpxx.h>

constexpr std::uint32_t prime_limit = 100'000;
constexpr std::string_view magic = "QBF1";

static void write_bytes(std::ostream &output, const char *data,
                        std::size_t size) {
  if (!output.write(data, size))
    throw std::runtime_error("Write failed");
}

static void read_bytes(std::istream &input, char *data, std::size_t size) {
  if (!input.read(data, size))
    throw std::runtime_error("Incomplete input");
}

static void write_uint(std::ostream &output, std::uint64_t value,
                       std::size_t size) {
  unsigned char bytes[8];
  for (std::size_t i = 0; i < size; ++i)
    bytes[i] = value >> (8 * i);
  write_bytes(output, reinterpret_cast<const char *>(bytes), size);
}

static std::uint64_t read_uint(std::istream &input, std::size_t size) {
  unsigned char bytes[8];
  read_bytes(input, reinterpret_cast<char *>(bytes), size);
  std::uint64_t value = 0;
  for (std::size_t i = 0; i < size; ++i)
    value |= std::uint64_t(bytes[i]) << (8 * i);
  return value;
}

static std::vector<std::uint32_t> primes() {
  std::vector<bool> composite(prime_limit + 1);
  std::vector<std::uint32_t> result;
  for (std::uint32_t p = 2; p <= prime_limit; ++p) {
    if (composite[p])
      continue;
    result.push_back(p);
    if (p > prime_limit / p)
      continue;
    for (std::uint32_t multiple = p * p; multiple <= prime_limit;
         multiple += p) {
      composite[multiple] = true;
    }
  }
  return result;
}

class Splitter {
public:
  Splitter(std::ostream &archive, std::ostream &report)
      : archive(archive), report(report), prime_list(primes()) {
    mpz_primorial_ui(primorial.get_mpz_t(), prime_limit);
    report << "offset_digits\tdigits\tprime_factors\tcofactor_bits\tstatus\n";
  }

  void add(std::string_view digits, std::uint64_t offset) {
    const mpz_class value(std::string(digits), 10);
    mpz_class shared;
    if (value > 1)
      mpz_gcd(shared.get_mpz_t(), value.get_mpz_t(), primorial.get_mpz_t());
    if (shared == 1 && digits.size() > 10) {
      const auto half = digits.size() / 2;
      add(digits.substr(0, half), offset);
      add(digits.substr(half), offset + half);
      return;
    }

    mpz_class cofactor = value;
    std::vector<std::pair<std::uint32_t, unsigned long>> factors;
    for (auto p : prime_list) {
      if (shared <= 1)
        break;
      if (!mpz_divisible_ui_p(shared.get_mpz_t(), p))
        continue;
      const mpz_class prime(static_cast<unsigned long>(p));
      const auto exponent = mpz_remove(cofactor.get_mpz_t(),
                                       cofactor.get_mpz_t(), prime.get_mpz_t());
      mpz_divexact_ui(shared.get_mpz_t(), shared.get_mpz_t(), p);
      factors.emplace_back(p, exponent);
    }
    if (shared > 1)
      throw std::runtime_error("Incomplete extraction of the shared factors");
    const auto bits =
        cofactor == 0 ? 0 : mpz_sizeinbase(cofactor.get_mpz_t(), 2);
    const auto size = (bits + 7) / 8;
    std::vector<char> bytes(size);
    if (size)
      mpz_export(bytes.data(), nullptr, 1, 1, 1, 0, cofactor.get_mpz_t());

    write_uint(archive, digits.size(), 4);
    write_uint(archive, factors.size(), 4);
    write_uint(archive, size, 4);
    for (const auto &[p, exponent] : factors) {
      write_uint(archive, p, 4);
      write_uint(archive, exponent, 4);
    }
    if (size)
      write_bytes(archive, bytes.data(), size);

    report << offset << '\t' << digits.size() << '\t';
    for (std::size_t i = 0; i < factors.size(); ++i) {
      if (i)
        report << " * ";
      report << factors[i].first << '^' << factors[i].second;
    }
    if (factors.empty())
      report << '-';
    report << '\t' << bits << '\t';
    if (value < 2)
      report << "zero_or_one";
    else if (cofactor == 1)
      report << "fully_factored";
    else if (cofactor <= 10'000'000'000UL)
      report << "prime_cofactor";
    else
      report << "partly_factored";
    report << std::endl;
    std::cout << "block " << ++blocks << " offset " << offset << " digits "
              << digits.size() << " distinct_prime_factors " << factors.size()
              << std::endl;
  }

private:
  std::ostream &archive;
  std::ostream &report;
  const std::vector<std::uint32_t> prime_list;
  mpz_class primorial;
  std::uint64_t blocks = 0;
};

static void split(const char *path, const char *archive_path,
                  const char *report_path, std::size_t width) {
  std::ifstream input(path, std::ios::binary);
  auto total_digits = std::filesystem::file_size(path);
  if (!input || total_digits == 0)
    throw std::runtime_error("Empty or unreadable decimal input");
  input.seekg(-1, std::ios::end);
  const bool newline = input.get() == '\n';
  if (newline)
    --total_digits;
  if (!total_digits)
    throw std::runtime_error("The input has no digits");
  input.seekg(0);

  std::ofstream archive(archive_path, std::ios::binary);
  std::ofstream report(report_path);
  if (!report)
    throw std::runtime_error("Cannot open the report");
  write_bytes(archive, magic.data(), magic.size());
  write_uint(archive, total_digits, 8);
  write_uint(archive, newline, 1);
  write_uint(archive, width, 4);

  Splitter splitter(archive, report);
  std::string digits;
  for (std::uint64_t offset = 0; offset < total_digits;
       offset += digits.size()) {
    digits.resize(std::min<std::uint64_t>(width, total_digits - offset));
    read_bytes(input, digits.data(), digits.size());
    if (digits.find_first_not_of("0123456789") != digits.npos) {
      throw std::runtime_error("Only one line of decimal digits is supported");
    }
    splitter.add(digits, offset);
  }
  archive.close();
  report.close();
  if (!archive || !report)
    throw std::runtime_error("Could not complete the split");
}

static void join(const char *archive_path, const char *output_path) {
  std::ifstream archive(archive_path, std::ios::binary);
  char header[magic.size()];
  read_bytes(archive, header, sizeof(header));
  if (std::string_view(header, sizeof(header)) != magic)
    throw std::runtime_error("Invalid archive magic");
  auto remaining = read_uint(archive, 8);
  const auto newline = read_uint(archive, 1);
  const auto max_width = read_uint(archive, 4);
  if (!remaining || !max_width || newline > 1)
    throw std::runtime_error("Invalid archive header");

  std::ofstream output(output_path, std::ios::binary);
  const auto prime_list = primes();
  std::uint64_t blocks = 0;
  while (remaining) {
    const auto width = read_uint(archive, 4);
    const auto count = read_uint(archive, 4);
    const auto size = read_uint(archive, 4);
    if (!width || width > max_width || width > remaining ||
        count > prime_list.size() || size > width) {
      throw std::runtime_error("Invalid block sizes");
    }
    mpz_class product = 1;
    std::uint64_t previous = 0;
    for (std::uint64_t i = 0; i < count; ++i) {
      const auto p = read_uint(archive, 4);
      const auto exponent = read_uint(archive, 4);
      if (p <= previous ||
          !std::binary_search(prime_list.begin(), prime_list.end(), p) ||
          !exponent || exponent > width * 4) {
        throw std::runtime_error("Invalid prime factor");
      }
      mpz_class power;
      mpz_ui_pow_ui(power.get_mpz_t(), p, exponent);
      product *= power;
      previous = p;
    }
    std::vector<char> bytes(size);
    mpz_class value = 0;
    if (size) {
      read_bytes(archive, bytes.data(), size);
      mpz_import(value.get_mpz_t(), size, 1, 1, 1, 0, bytes.data());
    }
    value *= product;
    const auto digits = value.get_str(10);
    if (digits.size() > width)
      throw std::runtime_error("Block value is too large");
    const std::string leading_zeros(width - digits.size(), '0');
    write_bytes(output, leading_zeros.data(), leading_zeros.size());
    write_bytes(output, digits.data(), digits.size());
    remaining -= width;
    std::cout << "restored block " << ++blocks << " digits " << width
              << std::endl;
  }
  if (archive.peek() != std::char_traits<char>::eof() || archive.bad()) {
    throw std::runtime_error("Unexpected bytes after the last block");
  }
  if (newline)
    write_bytes(output, "\n", 1);
  output.close();
  if (!output)
    throw std::runtime_error("Could not complete the join");
}

int main(int argc, char **argv) {
  try {
    if (argc == 6 && std::string_view(argv[1]) == "split") {
      std::size_t parsed;
      const std::string width_text(argv[5]);
      const auto width = std::stoull(width_text, &parsed);
      if (parsed != width_text.size() || width == 0 || width > UINT32_MAX) {
        throw std::runtime_error("Invalid maximum block width");
      }
      split(argv[2], argv[3], argv[4], width);
    } else if (argc == 4 && std::string_view(argv[1]) == "join") {
      join(argv[2], argv[3]);
    } else {
      std::cerr
          << "Usage: decimal-blocks split INPUT ARCHIVE REPORT MAX_DIGITS\n"
             "       decimal-blocks join ARCHIVE OUTPUT\n";
      return 2;
    }
  } catch (const std::exception &exception) {
    std::cerr << exception.what() << '\n';
    return 1;
  }
}
