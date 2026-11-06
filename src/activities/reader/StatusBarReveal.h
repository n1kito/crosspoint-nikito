#pragma once

#include <cstdint>

// Owned by ReaderActivity and accessed under RenderLock.
class StatusBarReveal {
 public:
  static constexpr uint32_t DURATION_MS = 5000;

  void show(uint32_t now) {
    startedAt = now;
    visible = true;
  }

  bool expire(uint32_t now) {
    if (!visible || static_cast<uint32_t>(now - startedAt) < DURATION_MS) return false;
    visible = false;
    return true;
  }

  bool isVisible() const { return visible; }

 private:
  uint32_t startedAt = 0;
  bool visible = false;
};
