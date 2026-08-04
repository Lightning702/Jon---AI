#pragma once

#include "ItemDatabase.hpp"

#include <string>
#include <vector>

namespace sf {

enum class RecipeKind : u32 {
    Handcraft = 0,
    Refine,
    Cook,
    Count
};

struct RecipeIngredient {
    ItemId id = ItemId::None;
    u32 amount = 1;
};

struct Recipe {
    u32 id = 0;
    std::string name;
    RecipeKind kind = RecipeKind::Handcraft;
    std::vector<RecipeIngredient> inputs;
    ItemId output = ItemId::None;
    u32 outputAmount = 1;
    f64 secondsPerBatch = 1.0;
    u32 requiredResearchTier = 1;
};

class RecipeDatabase {
public:
    static const RecipeDatabase& instance();

    const std::vector<Recipe>& all() const { return entries; }
    const Recipe* find(u32 id) const;
    std::vector<const Recipe*> forOutput(ItemId output) const;
    std::vector<const Recipe*> ofKind(RecipeKind kind) const;
    std::vector<const Recipe*> craftableFrom(const class Inventory& inventory, u32 researchTier) const;

    static const char* kindName(RecipeKind kind);

private:
    RecipeDatabase();
    std::vector<Recipe> entries;
};

class Inventory;

bool canCraft(const Recipe& recipe, const Inventory& inventory, u32 researchTier);
bool performCraft(const Recipe& recipe, Inventory& inventory, u32 researchTier);

}
