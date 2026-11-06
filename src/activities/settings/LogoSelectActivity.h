#pragma once

#include <array>

#include "activities/UiListActivity.h"
#include "util/CustomLogo.h"

class LogoSelectActivity final : public UiListActivity {
 public:
  LogoSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput);
  void onEnter() override;

 private:
  struct LogoFile {
    char name[CustomLogo::FILENAME_CAPACITY]{};
  };
  std::array<LogoFile, CustomLogo::MAX_FILES> files{};
  int fileCount = 0;

  int listCount() const override { return fileCount + 1; }
  const char* headerTitle() const override;
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  static void provideRow(void* context, uint16_t index, freeink::ui::ListItem& item);
};
