#include "EpubReaderMenuActivity.h"

#include <algorithm>

#include <GfxRenderer.h>
#include <I18n.h>

#include "CrossPointSettings.h"
#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "fontIds.h"

EpubReaderMenuActivity::EpubReaderMenuActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                               const std::string& title, const int currentPage, const int totalPages,
                                               const int bookProgressPercent, const uint8_t currentOrientation,
                                               const bool hasFootnotes)
    : Activity("EpubReaderMenu", renderer, mappedInput),
      menuItems(buildMenuItems(hasFootnotes)),
      title(title),
      pendingOrientation(currentOrientation),
      currentPage(currentPage),
      totalPages(totalPages),
      bookProgressPercent(bookProgressPercent) {}

std::vector<EpubReaderMenuActivity::MenuItem> EpubReaderMenuActivity::buildMenuItems(bool hasFootnotes) {
  std::vector<MenuItem> items;
  items.reserve(15);
  items.push_back({MenuAction::SELECT_CHAPTER, StrId::STR_SELECT_CHAPTER});
  if (hasFootnotes) {
    items.push_back({MenuAction::FOOTNOTES, StrId::STR_FOOTNOTES});
  }
  items.push_back({MenuAction::FONT_SIZE, StrId::STR_FONT_SIZE});
  items.push_back({MenuAction::LINE_SPACING, StrId::STR_LINE_SPACING});
  items.push_back({MenuAction::SCREEN_MARGIN, StrId::STR_SCREEN_MARGIN});
  items.push_back({MenuAction::PARAGRAPH_ALIGNMENT, StrId::STR_PARA_ALIGNMENT});
  items.push_back({MenuAction::HYPHENATION, StrId::STR_HYPHENATION});
  items.push_back({MenuAction::ROTATE_SCREEN, StrId::STR_ORIENTATION});
  items.push_back({MenuAction::AUTO_PAGE_TURN, StrId::STR_AUTO_TURN_PAGES_PER_MIN});
  items.push_back({MenuAction::GO_TO_PERCENT, StrId::STR_GO_TO_PERCENT});
  items.push_back({MenuAction::SCREENSHOT, StrId::STR_SCREENSHOT_BUTTON});
  items.push_back({MenuAction::DISPLAY_QR, StrId::STR_DISPLAY_QR});
  items.push_back({MenuAction::GO_HOME, StrId::STR_GO_HOME_BUTTON});
  items.push_back({MenuAction::SYNC, StrId::STR_SYNC_PROGRESS});
  items.push_back({MenuAction::DELETE_CACHE, StrId::STR_DELETE_CACHE});
  return items;
}

void EpubReaderMenuActivity::onEnter() {
  Activity::onEnter();
  requestUpdate();
}

void EpubReaderMenuActivity::onExit() { Activity::onExit(); }

void EpubReaderMenuActivity::loop() {
  // Handle navigation
  buttonNavigator.onNext([this] {
    selectedIndex = ButtonNavigator::nextIndex(selectedIndex, static_cast<int>(menuItems.size()));
    requestUpdate();
  });

  buttonNavigator.onPrevious([this] {
    selectedIndex = ButtonNavigator::previousIndex(selectedIndex, static_cast<int>(menuItems.size()));
    requestUpdate();
  });

  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    const auto selectedAction = menuItems[selectedIndex].action;
    if (selectedAction == MenuAction::ROTATE_SCREEN) {
      // Cycle orientation preview locally; actual rotation happens on menu exit.
      pendingOrientation = (pendingOrientation + 1) % orientationLabels.size();
      requestUpdate();
      return;
    }

    if (selectedAction == MenuAction::AUTO_PAGE_TURN) {
      selectedPageTurnOption = (selectedPageTurnOption + 1) % pageTurnLabels.size();
      requestUpdate();
      return;
    }

    if (selectedAction == MenuAction::FONT_SIZE) {
      SETTINGS.fontSize = (SETTINGS.fontSize + 1) % CrossPointSettings::FONT_SIZE_COUNT;
      SETTINGS.saveToFile();
      settingsChanged = true;
      requestUpdate();
      return;
    }

    if (selectedAction == MenuAction::LINE_SPACING) {
      SETTINGS.lineSpacing = (SETTINGS.lineSpacing + 1) % CrossPointSettings::LINE_COMPRESSION_COUNT;
      SETTINGS.saveToFile();
      settingsChanged = true;
      requestUpdate();
      return;
    }

    if (selectedAction == MenuAction::SCREEN_MARGIN) {
      SETTINGS.screenMargin = (SETTINGS.screenMargin >= 40) ? 5 : SETTINGS.screenMargin + 5;
      SETTINGS.saveToFile();
      settingsChanged = true;
      requestUpdate();
      return;
    }

    if (selectedAction == MenuAction::PARAGRAPH_ALIGNMENT) {
      SETTINGS.paragraphAlignment = (SETTINGS.paragraphAlignment + 1) % CrossPointSettings::PARAGRAPH_ALIGNMENT_COUNT;
      SETTINGS.saveToFile();
      settingsChanged = true;
      requestUpdate();
      return;
    }

    if (selectedAction == MenuAction::HYPHENATION) {
      SETTINGS.hyphenationEnabled = !SETTINGS.hyphenationEnabled;
      SETTINGS.saveToFile();
      settingsChanged = true;
      requestUpdate();
      return;
    }

    setResult(MenuResult{static_cast<int>(selectedAction), pendingOrientation, selectedPageTurnOption, settingsChanged});
    finish();
    return;
  } else if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    ActivityResult result;
    result.isCancelled = true;
    result.data = MenuResult{-1, pendingOrientation, selectedPageTurnOption, settingsChanged};
    setResult(std::move(result));
    finish();
    return;
  }
}

void EpubReaderMenuActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const auto pageWidth = renderer.getScreenWidth();
  const auto orientation = renderer.getOrientation();
  // Landscape orientation: button hints are drawn along a vertical edge, so we
  // reserve a horizontal gutter to prevent overlap with menu content.
  const bool isLandscapeCw = orientation == GfxRenderer::Orientation::LandscapeClockwise;
  const bool isLandscapeCcw = orientation == GfxRenderer::Orientation::LandscapeCounterClockwise;
  // Inverted portrait: button hints appear near the logical top, so we reserve
  // vertical space to keep the header and list clear.
  const bool isPortraitInverted = orientation == GfxRenderer::Orientation::PortraitInverted;
  const int hintGutterWidth = (isLandscapeCw || isLandscapeCcw) ? 30 : 0;
  // Landscape CW places hints on the left edge; CCW keeps them on the right.
  const int contentX = isLandscapeCw ? hintGutterWidth : 0;
  const int contentWidth = pageWidth - hintGutterWidth;
  const int hintGutterHeight = isPortraitInverted ? 50 : 0;
  const int contentY = hintGutterHeight;

  // Title
  const std::string truncTitle =
      renderer.truncatedText(UI_12_FONT_ID, title.c_str(), contentWidth - 40, EpdFontFamily::BOLD);
  // Manual centering so we can respect the content gutter.
  const int titleX =
      contentX + (contentWidth - renderer.getTextWidth(UI_12_FONT_ID, truncTitle.c_str(), EpdFontFamily::BOLD)) / 2;
  renderer.drawText(UI_12_FONT_ID, titleX, 15 + contentY, truncTitle.c_str(), true, EpdFontFamily::BOLD);

  // Progress summary
  std::string progressLine;
  if (totalPages > 0) {
    progressLine = std::string(tr(STR_CHAPTER_PREFIX)) + std::to_string(currentPage) + "/" +
                   std::to_string(totalPages) + std::string(tr(STR_PAGES_SEPARATOR));
  }
  progressLine += std::string(tr(STR_BOOK_PREFIX)) + std::to_string(bookProgressPercent) + "%";
  renderer.drawCenteredText(UI_10_FONT_ID, 45, progressLine.c_str());

  // Menu Items
  const int startY = 75 + contentY;
  constexpr int lineHeight = 30;
  const int footerReservedHeight = 35;
  const int availableHeight = renderer.getScreenHeight() - startY - footerReservedHeight;
  const int maxVisibleItems = std::max(1, availableHeight / lineHeight);
  int firstVisibleIndex = 0;
  if (static_cast<int>(menuItems.size()) > maxVisibleItems) {
    const int centeredStart = selectedIndex - (maxVisibleItems / 2);
    const int maxStart = static_cast<int>(menuItems.size()) - maxVisibleItems;
    firstVisibleIndex = std::max(0, std::min(centeredStart, maxStart));
  }
  const int endVisibleIndex = std::min(static_cast<int>(menuItems.size()), firstVisibleIndex + maxVisibleItems);

  const std::vector<StrId> fontSizeLabels = {StrId::STR_SMALL, StrId::STR_MEDIUM, StrId::STR_LARGE,
                                             StrId::STR_X_LARGE};
  const std::vector<StrId> lineSpacingLabels = {StrId::STR_TIGHT, StrId::STR_NORMAL, StrId::STR_WIDE};
  const std::vector<StrId> paragraphAlignmentLabels = {StrId::STR_JUSTIFY, StrId::STR_ALIGN_LEFT, StrId::STR_CENTER,
                                                       StrId::STR_ALIGN_RIGHT, StrId::STR_BOOK_S_STYLE};

  for (int i = firstVisibleIndex; i < endVisibleIndex; ++i) {
    const int displayY = startY + ((i - firstVisibleIndex) * lineHeight);
    const bool isSelected = (i == selectedIndex);

    if (isSelected) {
      // Highlight only the content area so we don't paint over hint gutters.
      renderer.fillRect(contentX, displayY, contentWidth - 1, lineHeight, true);
    }

    renderer.drawText(UI_10_FONT_ID, contentX + 20, displayY, I18N.get(menuItems[i].labelId), !isSelected);

    const auto drawValue = [this, contentX, contentWidth, displayY, isSelected](const char* value) {
      const auto width = renderer.getTextWidth(UI_10_FONT_ID, value);
      renderer.drawText(UI_10_FONT_ID, contentX + contentWidth - 20 - width, displayY, value, !isSelected);
    };

    switch (menuItems[i].action) {
      case MenuAction::FONT_SIZE:
        drawValue(I18N.get(fontSizeLabels[SETTINGS.fontSize]));
        break;
      case MenuAction::LINE_SPACING:
        drawValue(I18N.get(lineSpacingLabels[SETTINGS.lineSpacing]));
        break;
      case MenuAction::SCREEN_MARGIN: {
        const auto value = std::to_string(SETTINGS.screenMargin);
        drawValue(value.c_str());
        break;
      }
      case MenuAction::PARAGRAPH_ALIGNMENT:
        drawValue(I18N.get(paragraphAlignmentLabels[SETTINGS.paragraphAlignment]));
        break;
      case MenuAction::HYPHENATION:
        drawValue(I18N.get(SETTINGS.hyphenationEnabled ? StrId::STR_STATE_ON : StrId::STR_STATE_OFF));
        break;
      case MenuAction::ROTATE_SCREEN: {
        const char* value = I18N.get(orientationLabels[pendingOrientation]);
        drawValue(value);
        break;
      }
      case MenuAction::AUTO_PAGE_TURN: {
        const auto value = pageTurnLabels[selectedPageTurnOption];
        drawValue(value);
        break;
      }
      default:
        break;
    }
  }

  // Footer / Hints
  const auto labels = mappedInput.mapLabels(tr(STR_BACK), tr(STR_SELECT), tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);

  renderer.displayBuffer();
}
