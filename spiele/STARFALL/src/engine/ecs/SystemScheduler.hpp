#pragma once

#include "System.hpp"

#include <memory>
#include <vector>

namespace sf {

class SystemScheduler {
public:
    void add(std::unique_ptr<System> system);
    void rebuildGroups();
    void execute(World& world, f64 stepSeconds);
    void executeStage(World& world, SystemStage stage, f64 stepSeconds);

    usize systemCount() const { return systems.size(); }
    usize parallelGroupCount() const { return groups.size(); }
    const System& systemAt(usize index) const { return *systems[index]; }

private:
    struct ParallelGroup {
        SystemStage stage = SystemStage::Simulation;
        std::vector<u32> members;
    };

    std::vector<std::unique_ptr<System>> systems;
    std::vector<ParallelGroup> groups;
    bool dirty = true;
};

}
