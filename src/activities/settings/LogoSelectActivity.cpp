#include "LogoSelectActivity.h"

#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>
#include <Logging.h>

#include <algorithm>
#include <cstdio>
#include <cstring>

#include "CrossPointSettings.h"
#include "components/UITheme.h"

namespace fui = freeink::ui;

LogoSelectActivity::LogoSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : UiListActivity("LogoSelect", renderer, mappedInput) {}

void LogoSelectActivity::onEnter() {
  UiListActivity::onEnter();
  fileCount = 0;
  if (Storage.exists("/logos")) {
    auto directory = Storage.open("/logos");
    if (directory && directory.isDirectory()) {
      while (fileCount < static_cast<int>(files.size())) {
        auto file = directory.openNextFile();
        if (!file) break;
        if (file.isDirectory()) continue;
        char name[CustomLogo::FILENAME_CAPACITY + 1];
        const size_t length = file.getName(name, sizeof(name));
        file.close();
        if (length == 0 || length >= sizeof(name) - 1 || !CustomLogo::validFile(name)) continue;
        snprintf(files[fileCount++].name, sizeof(files[0].name), "%s", name);
      }
    }
  }
  std::sort(files.begin(), files.begin() + fileCount,
            [](const LogoFile& a, const LogoFile& b) { return strcmp(a.name, b.name) < 0; });
  int selected = 0;
  for (int i = 0; i < fileCount; ++i) {
    if (strcmp(files[i].name, SETTINGS.logoFilename) == 0) selected = i + 1;
  }
  nav.reset(selected);
}

const char* LogoSelectActivity::headerTitle() const { return tr(STR_LOGO); }

void LogoSelectActivity::activateIndex(const int index) {
  if (index < 0 || index >= listCount()) return;
  app.clearTapFlash();
  const char* name = index == 0 ? "" : files[index - 1].name;
  if (strcmp(name, SETTINGS.logoFilename) != 0) {
    snprintf(SETTINGS.logoFilename, sizeof(SETTINGS.logoFilename), "%s", name);
    SETTINGS.saveToFile();
  }
  finish();
}

void LogoSelectActivity::provideRow(void* context, const uint16_t index, fui::ListItem& item) {
  auto& self = *static_cast<LogoSelectActivity*>(context);
  if (index >= self.listCount()) return;
  const char* name = index == 0 ? "" : self.files[index - 1].name;
  item.label = index == 0 ? tr(STR_DEFAULT_LOGO) : name;
  item.value = strcmp(name, SETTINGS.logoFilename) == 0 ? tr(STR_SELECTED) : nullptr;
  item.actionValue = static_cast<int16_t>(index);
}

void LogoSelectActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  screen.setContentMarginFromScreen(fui::Insets{static_cast<int16_t>(metrics.topPadding + metrics.headerHeight), 0,
                                                static_cast<int16_t>(metrics.buttonHintsHeight), 0});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));
  fui::ListProps props;
  props.rowProvider = &LogoSelectActivity::provideRow;
  props.rowProviderCtx = this;
  props.count = static_cast<uint16_t>(listCount());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  props.labelText = screen.theme().smallText;
  props.labelText.maxLines = 2;
  syncListViewport(screen, props);
  screen.list(props);
}
