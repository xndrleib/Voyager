// Craft 8 oak_planks from 2 oak_log (do the recipe 2 times): craftItem(bot, "oak_planks", 2);
async function craftItem(bot, name, count = 1) {
    // Locate crafting table
    const craftingTable = bot.findBlock({
        matching: mcData.blocksByName.crafting_table.id,
        maxDistance: 32
    });

    if (!craftingTable) {
        bot.chat("Craft without a crafting table");
    } else {
        await bot.pathfinder.goto(
            new GoalLookAtBlock(craftingTable.position, bot.world)
        );
    }

    const recipes = bot.recipesFor(itemByName.id, null, 1, craftingTable);
    if (recipes && recipes.length > 0) {
        const recipe = recipes[0];
        await bot.craft(recipe, count, craftingTable);
    }
}
