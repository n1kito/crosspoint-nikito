#pragma once

#include <cstddef>
#include <string_view>

class GfxRenderer;

namespace CustomLogo {
inline constexpr int SIZE = 120;
inline constexpr size_t FILENAME_CAPACITY = 96;
inline constexpr size_t MAX_FILES = 32;

bool validFilename(std::string_view name);
bool validFile(const char* name);
void draw(GfxRenderer& renderer);
}  // namespace CustomLogo
