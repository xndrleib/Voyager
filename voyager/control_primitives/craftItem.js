async function craftItem(bot, name, count = 1) {
    // Validate inputs
    if (typeof name !== "string") {
        throw new Error("name for craftItem must be a string");
    }
    if (typeof count !== "number") {
        throw new Error("count for craftItem must be a number");
    }

    // Ensure item exists
    const itemByName = mcData.itemsByName[name];
    if (!itemByName) {
        throw new Error(`No item named ${name}`);
    }

    // Locate crafting table
    const craftingTable = bot.findBlock({
        matching: mcData.blocksByName.crafting_table.id,
        maxDistance: 32
    });

    // Handling when crafting table is not found
    if (!craftingTable) {
        throw new Error("No crafting table found within reach. I need a crafting table to proceed.");
    } else {
        await bot.pathfinder.goto(new GoalLookAtBlock(craftingTable.position, bot.world));
    }

    // Fetch the recipe
    const recipes = bot.recipesFor(itemByName.id, null, 1, craftingTable);
    if (!recipes || recipes.length === 0) {
        throw new Error("No available recipe for ${name}.");
    }
    const recipe = recipes[0];

    // Attempt to craft
    try {
        await bot.craft(recipe, count, craftingTable);
        bot.chat(`Crafted ${name} ${count} times.`);
    } catch (error) {
        bot.chat(`Failed to craft ${name} ${count} times. Error: ${error.message}`);
    }
}
