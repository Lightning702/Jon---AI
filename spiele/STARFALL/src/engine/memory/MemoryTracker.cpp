#include "MemoryTracker.hpp"

#include "../core/Log.hpp"

#include <cstdio>
#include <mutex>

namespace sf {
namespace {

std::mutex& trackerMutex() {
    static std::mutex instance;
    return instance;
}

constexpr usize kMegabyte = 1024ull * 1024ull;

}

MemoryTracker::MemoryTracker() {
    budgets[static_cast<usize>(MemoryCategory::Core)].limitBytes = 128 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Render)].limitBytes = 2048 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Terrain)].limitBytes = 3072 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Universe)].limitBytes = 1024 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Physics)].limitBytes = 512 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Audio)].limitBytes = 256 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Network)].limitBytes = 128 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Gameplay)].limitBytes = 512 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Interface)].limitBytes = 128 * kMegabyte;
    budgets[static_cast<usize>(MemoryCategory::Scratch)].limitBytes = 256 * kMegabyte;
}

MemoryTracker& MemoryTracker::instance() {
    static MemoryTracker tracker;
    return tracker;
}

void MemoryTracker::setBudget(MemoryCategory category, usize limitBytes) {
    std::lock_guard<std::mutex> lock(trackerMutex());
    budgets[static_cast<usize>(category)].limitBytes = limitBytes;
}

void MemoryTracker::recordAllocation(MemoryCategory category, usize bytes) {
    std::lock_guard<std::mutex> lock(trackerMutex());
    MemoryBudget& entry = budgets[static_cast<usize>(category)];
    entry.currentBytes += bytes;
    entry.allocationCount += 1;
    if (entry.currentBytes > entry.peakBytes) entry.peakBytes = entry.currentBytes;
}

void MemoryTracker::recordDeallocation(MemoryCategory category, usize bytes) {
    std::lock_guard<std::mutex> lock(trackerMutex());
    MemoryBudget& entry = budgets[static_cast<usize>(category)];
    entry.currentBytes = bytes > entry.currentBytes ? 0 : entry.currentBytes - bytes;
}

MemoryBudget MemoryTracker::budget(MemoryCategory category) const {
    std::lock_guard<std::mutex> lock(trackerMutex());
    return budgets[static_cast<usize>(category)];
}

usize MemoryTracker::totalBytes() const {
    std::lock_guard<std::mutex> lock(trackerMutex());
    usize total = 0;
    for (usize index = 0; index < static_cast<usize>(MemoryCategory::Count); ++index) {
        total += budgets[index].currentBytes;
    }
    return total;
}

bool MemoryTracker::overBudget(MemoryCategory category) const {
    std::lock_guard<std::mutex> lock(trackerMutex());
    const MemoryBudget& entry = budgets[static_cast<usize>(category)];
    return entry.limitBytes > 0 && entry.currentBytes > entry.limitBytes;
}

std::string MemoryTracker::report() const {
    std::lock_guard<std::mutex> lock(trackerMutex());
    std::string text;
    char line[192];
    for (usize index = 0; index < static_cast<usize>(MemoryCategory::Count); ++index) {
        const MemoryBudget& entry = budgets[index];
        std::snprintf(line, sizeof(line), "%-10s %8.2f MB / %8.2f MB  Spitze %8.2f MB\n",
                      categoryName(static_cast<MemoryCategory>(index)),
                      static_cast<f64>(entry.currentBytes) / static_cast<f64>(kMegabyte),
                      static_cast<f64>(entry.limitBytes) / static_cast<f64>(kMegabyte),
                      static_cast<f64>(entry.peakBytes) / static_cast<f64>(kMegabyte));
        text += line;
    }
    return text;
}

void MemoryTracker::enforceBudgets() const {
    for (usize index = 0; index < static_cast<usize>(MemoryCategory::Count); ++index) {
        const MemoryCategory category = static_cast<MemoryCategory>(index);
        if (!overBudget(category)) continue;
        const MemoryBudget entry = budget(category);
        logError("memory", "Budget ueberschritten: %s %.2f MB von %.2f MB", categoryName(category),
                 static_cast<f64>(entry.currentBytes) / static_cast<f64>(kMegabyte),
                 static_cast<f64>(entry.limitBytes) / static_cast<f64>(kMegabyte));
    }
}

const char* MemoryTracker::categoryName(MemoryCategory category) {
    switch (category) {
        case MemoryCategory::Core: return "core";
        case MemoryCategory::Render: return "render";
        case MemoryCategory::Terrain: return "terrain";
        case MemoryCategory::Universe: return "universe";
        case MemoryCategory::Physics: return "physics";
        case MemoryCategory::Audio: return "audio";
        case MemoryCategory::Network: return "network";
        case MemoryCategory::Gameplay: return "gameplay";
        case MemoryCategory::Interface: return "interface";
        case MemoryCategory::Scratch: return "scratch";
        case MemoryCategory::Count: return "count";
    }
    return "unknown";
}

}
