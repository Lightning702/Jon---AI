#include "SystemScheduler.hpp"

#include "../job/JobSystem.hpp"

namespace sf {

void SystemScheduler::add(std::unique_ptr<System> system) {
    if (!system) return;
    systems.push_back(std::move(system));
    dirty = true;
}

void SystemScheduler::rebuildGroups() {
    groups.clear();
    for (u32 stageIndex = 0; stageIndex < static_cast<u32>(SystemStage::Count); ++stageIndex) {
        const SystemStage stage = static_cast<SystemStage>(stageIndex);
        std::vector<u32> pending;
        for (u32 index = 0; index < systems.size(); ++index) {
            if (systems[index]->systemStage() == stage) pending.push_back(index);
        }
        while (!pending.empty()) {
            ParallelGroup group;
            group.stage = stage;
            std::vector<u32> remaining;
            for (u32 candidate : pending) {
                bool conflicts = false;
                for (u32 member : group.members) {
                    if (systems[candidate]->conflictsWith(*systems[member])) {
                        conflicts = true;
                        break;
                    }
                }
                if (conflicts) remaining.push_back(candidate);
                else group.members.push_back(candidate);
            }
            groups.push_back(group);
            pending = remaining;
        }
    }
    dirty = false;
}

void SystemScheduler::execute(World& world, f64 stepSeconds) {
    if (dirty) rebuildGroups();
    for (const ParallelGroup& group : groups) {
        if (group.members.size() == 1) {
            systems[group.members[0]]->execute(world, stepSeconds);
            continue;
        }
        std::vector<std::function<void()>> batch;
        for (u32 member : group.members) {
            System* system = systems[member].get();
            batch.push_back([system, &world, stepSeconds]() { system->execute(world, stepSeconds); });
        }
        JobHandle handle = JobSystem::instance().scheduleBatch(batch);
        JobSystem::instance().wait(handle);
    }
}

void SystemScheduler::executeStage(World& world, SystemStage stage, f64 stepSeconds) {
    if (dirty) rebuildGroups();
    for (const ParallelGroup& group : groups) {
        if (group.stage != stage) continue;
        if (group.members.size() == 1) {
            systems[group.members[0]]->execute(world, stepSeconds);
            continue;
        }
        std::vector<std::function<void()>> batch;
        for (u32 member : group.members) {
            System* system = systems[member].get();
            batch.push_back([system, &world, stepSeconds]() { system->execute(world, stepSeconds); });
        }
        JobHandle handle = JobSystem::instance().scheduleBatch(batch);
        JobSystem::instance().wait(handle);
    }
}

}
