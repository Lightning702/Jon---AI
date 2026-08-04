#pragma once

#include "Allocator.hpp"

#include <string>

namespace sf {

struct MemoryBudget {
    usize limitBytes = 0;
    usize currentBytes = 0;
    usize peakBytes = 0;
    u64 allocationCount = 0;
};

class MemoryTracker {
public:
    static MemoryTracker& instance();

    void setBudget(MemoryCategory category, usize limitBytes);
    void recordAllocation(MemoryCategory category, usize bytes);
    void recordDeallocation(MemoryCategory category, usize bytes);

    MemoryBudget budget(MemoryCategory category) const;
    usize totalBytes() const;
    bool overBudget(MemoryCategory category) const;
    std::string report() const;
    void enforceBudgets() const;

    static const char* categoryName(MemoryCategory category);

private:
    MemoryTracker();
    MemoryBudget budgets[static_cast<usize>(MemoryCategory::Count)];
};

}
