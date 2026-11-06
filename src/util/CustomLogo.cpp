#include "CustomLogo.h"

#include <Bitmap.h>
#include <FsHelpers.h>
#include <GfxRenderer.h>
#include <HalStorage.h>
#include <Logging.h>
#include <Memory.h>

#include <cstdio>

#include "CrossPointSettings.h"
#include "images/Logo120.h"

namespace {
constexpr size_t MAX_FILE_BYTES = 4096;

std::unique_ptr<Bitmap> openLogo(const char* name, HalFile& file) {
  if (!CustomLogo::validFilename(name)) return nullptr;
  char path[128];
  snprintf(path, sizeof(path), "/logos/%s", name);
  if (!Storage.openFileForRead("LOGO", path, file)) return nullptr;
  if (file.isDirectory() || file.size() > MAX_FILE_BYTES) {
    LOG_ERR("LOGO", "Logo exceeds %u bytes or is a directory: %s", (unsigned)MAX_FILE_BYTES, name);
    return nullptr;
  }
  auto bitmap = makeUniqueNoThrow<Bitmap>(file);
  if (!bitmap) {
    LOG_ERR("LOGO", "OOM: %u-byte bitmap", (unsigned)sizeof(Bitmap));
    return nullptr;
  }
  const auto error = bitmap->parseHeaders();
  if (error != BmpReaderError::Ok || !bitmap->is1Bit() || bitmap->getWidth() > CustomLogo::SIZE ||
      bitmap->getHeight() > CustomLogo::SIZE || file.position() > file.size() ||
      static_cast<size_t>(bitmap->getRowBytes()) * bitmap->getHeight() > file.size() - file.position()) {
    LOG_ERR("LOGO", "Expected a complete 1-bit BMP up to 120x120: %s (%s)", name, Bitmap::errorToString(error));
    return nullptr;
  }
  return bitmap;
}
}  // namespace

bool CustomLogo::validFilename(const std::string_view name) {
  return !name.empty() && name.size() < FILENAME_CAPACITY && name.front() != '.' &&
         name.find_first_of("/\\") == std::string_view::npos && FsHelpers::hasBmpExtension(name);
}

bool CustomLogo::validFile(const char* name) {
  HalFile file;
  return openLogo(name, file) != nullptr;
}

void CustomLogo::draw(GfxRenderer& renderer) {
  if (SETTINGS.logoFilename[0] != '\0') {
    HalFile file;
    auto bitmap = openLogo(SETTINGS.logoFilename, file);
    if (bitmap && renderer.drawBitmap(*bitmap, (renderer.getScreenWidth() - bitmap->getWidth()) / 2,
                                      (renderer.getScreenHeight() - bitmap->getHeight()) / 2, SIZE, SIZE)) {
      return;
    }
    LOG_ERR("LOGO", "Using default logo instead of %s", SETTINGS.logoFilename);
  }
  renderer.drawImage(Logo120, (renderer.getScreenWidth() - SIZE) / 2, (renderer.getScreenHeight() - SIZE) / 2, SIZE,
                     SIZE);
}
