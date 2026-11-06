"""Compile the production logo loader and BMP parser against host storage."""

from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

STORAGE = r"""
#pragma once
#include <cstdint>
#include <cstdio>
#include <string>
#include <filesystem>
class HalFile {
 public:
  ~HalFile() { if (file) std::fclose(file); }
  bool open(const std::string& name) { path = name; file = std::fopen(name.c_str(), "rb"); return file; }
  bool isDirectory() const { return std::filesystem::is_directory(path); }
  size_t size() const {
    if (!file) return 0;
    long pos = std::ftell(file);
    std::fseek(file, 0, SEEK_END);
    long end = std::ftell(file);
    std::fseek(file, pos, SEEK_SET);
    return end > 0 ? static_cast<size_t>(end) : 0;
  }
  size_t position() const { return static_cast<size_t>(std::ftell(file)); }
  bool seek(size_t pos) { return std::fseek(file, static_cast<long>(pos), SEEK_SET) == 0; }
  bool seekCur(size_t n) { return std::fseek(file, static_cast<long>(n), SEEK_CUR) == 0; }
  int read() { return std::fgetc(file); }
  size_t read(void* data, size_t n) { return std::fread(data, 1, n, file); }
  explicit operator bool() const { return file != nullptr; }
 private:
  std::FILE* file = nullptr;
  std::string path;
};
struct HostStorage {
  std::string root;
  int opens = 0;
  bool openFileForRead(const char*, const char* name, HalFile& file) {
    ++opens;
    return file.open(root + name);
  }
};
inline HostStorage Storage;
"""

RENDERER = r"""
#pragma once
#include <Bitmap.h>
class GfxRenderer {
 public:
  int custom = 0, builtin = 0, x = 0, y = 0;
  bool failDraw = false;
  int getScreenWidth() const { return 552; }
  int getScreenHeight() const { return 768; }
  bool drawBitmap(const Bitmap& bitmap, int px, int py, int, int) {
    x = px; y = py; ++custom;
    uint8_t row[46];
    for (int i = 0; i < bitmap.getHeight(); ++i) {
      if (bitmap.readNextRow(row, row + 30) != BmpReaderError::Ok) return false;
    }
    return !failDraw;
  }
  void drawImage(const uint8_t*, int px, int py, int, int) { x = px; y = py; ++builtin; }
};
"""

HARNESS = r"""
#include <cassert>
#include <cstring>
#include <GfxRenderer.h>
#include <CrossPointSettings.h>
#include "util/CustomLogo.h"
int main(int argc, char** argv) {
  assert(argc == 2);
  Storage.root = argv[1];
  assert(CustomLogo::validFilename("flower.BMP"));
  for (const char* name : {"", "../flower.bmp", "/flower.bmp", "a/b.bmp", "a\\b.bmp", ".hidden.bmp", "x.png"}) {
    assert(!CustomLogo::validFilename(name));
  }
  assert(!CustomLogo::validFilename(std::string(96, 'a') + ".bmp"));
  GfxRenderer renderer;
  CustomLogo::draw(renderer);
  assert(renderer.builtin == 1 && renderer.custom == 0 && Storage.opens == 0);

  assert(CustomLogo::validFile("flower.bmp"));
  std::strcpy(SETTINGS.logoFilename, "flower.bmp");
  CustomLogo::draw(renderer);
  assert(renderer.custom == 1 && renderer.builtin == 1);
  assert(renderer.x == 216 && renderer.y == 324);

  std::strcpy(SETTINGS.logoFilename, "small.bmp");
  CustomLogo::draw(renderer);
  assert(renderer.custom == 2 && renderer.builtin == 1);
  assert(renderer.x == 236 && renderer.y == 354);

  for (const char* name : {"missing.bmp", "truncated.bmp", "oversized.bmp", "huge.bmp", "color.bmp", "bad.bmp", "directory.bmp"}) {
    assert(!CustomLogo::validFile(name));
    std::strcpy(SETTINGS.logoFilename, name);
    const int fallbackBefore = renderer.builtin;
    CustomLogo::draw(renderer);
    assert(renderer.builtin == fallbackBefore + 1);
    assert(std::strcmp(SETTINGS.logoFilename, name) == 0);
  }
  std::strcpy(SETTINGS.logoFilename, "flower.bmp");
  renderer.failDraw = true;
  const int before = renderer.builtin;
  CustomLogo::draw(renderer);
  assert(renderer.builtin == before + 1);
}
"""


def bmp(width, height, bpp=1):
    stride = ((width * bpp + 31) // 32) * 4
    palette = b"\0\0\0\0\xff\xff\xff\0" if bpp == 1 else b""
    offset = 54 + len(palette)
    pixels = b"\xff" * (stride * height)
    return (struct.pack("<2sIHHI", b"BM", offset + len(pixels), 0, 0, offset)
            + struct.pack("<IiiHHIIiiII", 40, width, height, 1, bpp, 0, len(pixels), 0, 0, 0, 0)
            + palette + pixels)


with tempfile.TemporaryDirectory(prefix="crosspoint-logo-") as directory:
    temporary = Path(directory)
    stubs = temporary / "stubs"
    stubs.mkdir()
    (stubs / "HalStorage.h").write_text(STORAGE)
    (stubs / "GfxRenderer.h").write_text(RENDERER)
    (stubs / "CrossPointSettings.h").write_text(
        '#pragma once\nstruct HostSettings { char logoFilename[96] = ""; };\ninline HostSettings SETTINGS;\n')
    (stubs / "Logging.h").write_text('#pragma once\n#define LOG_ERR(...) ((void)0)\n')
    (stubs / "FsHelpers.h").write_text(r"""
#pragma once
#include <cctype>
#include <string_view>
namespace FsHelpers {
inline bool hasBmpExtension(std::string_view name) {
  if (name.size() < 4) return false;
  auto extension = name.substr(name.size() - 4);
  return extension[0] == '.' && std::tolower(extension[1]) == 'b' &&
         std::tolower(extension[2]) == 'm' && std::tolower(extension[3]) == 'p';
}
}
""")
    logos = temporary / "logos"
    logos.mkdir()
    shutil.copyfile(ROOT / "sd-card/logos/flower.bmp", logos / "flower.bmp")
    for name, contents in {
        "small.bmp": bmp(80, 60),
        "truncated.bmp": bmp(120, 120)[:-1],
        "oversized.bmp": bmp(121, 120),
        "huge.bmp": b"x" * 4097,
        "color.bmp": bmp(10, 10, 24),
        "bad.bmp": b"invalid BMP",
    }.items():
        (logos / name).write_bytes(contents)
    (logos / "directory.bmp").mkdir()
    source = temporary / "test.cpp"
    source.write_text(HARNESS)
    executable = temporary / "test"
    subprocess.run([
        "c++", "-std=c++20", "-Wall", "-Wextra", "-I", str(stubs),
        "-I", str(ROOT / "src"), "-I", str(ROOT / "lib/GfxRenderer"),
        "-I", str(ROOT / "lib/Memory"), str(source),
        str(ROOT / "src/util/CustomLogo.cpp"), str(ROOT / "lib/GfxRenderer/Bitmap.cpp"),
        str(ROOT / "lib/GfxRenderer/BitmapHelpers.cpp"), "-o", str(executable),
    ], check=True)
    subprocess.run([str(executable), str(temporary)], check=True)
print("Custom logo loading and fallback checks passed")
