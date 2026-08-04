#pragma once

#include "../container/BitSet.hpp"
#include "World.hpp"

#include <string>

namespace sf {

enum class SystemStage : u32 {
    Input = 0,
    Simulation,
    Physics,
    Gameplay,
    Presentation,
    Count
};

class System {
public:
    explicit System(std::string systemName, SystemStage systemStage)
        : name(std::move(systemName)), stage(systemStage) {
        readSet.resize(kMaximumComponentTypes);
        writeSet.resize(kMaximumComponentTypes);
    }

    virtual ~System() = default;
    virtual void execute(World& world, f64 stepSeconds) = 0;

    template <typename T>
    void declareRead() { readSet.set(ComponentTraits<T>::id()); }

    template <typename T>
    void declareWrite() { writeSet.set(ComponentTraits<T>::id()); }

    const std::string& systemName() const { return name; }
    SystemStage systemStage() const { return stage; }
    const BitSet& reads() const { return readSet; }
    const BitSet& writes() const { return writeSet; }

    bool conflictsWith(const System& other) const {
        return writeSet.intersects(other.writeSet) || writeSet.intersects(other.readSet) ||
               readSet.intersects(other.writeSet);
    }

private:
    std::string name;
    SystemStage stage;
    BitSet readSet;
    BitSet writeSet;
};

}
