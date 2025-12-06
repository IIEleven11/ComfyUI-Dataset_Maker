import { app } from "../../scripts/app.js";

app.registerExtension({
	name: "DatasetMaker.LoraList",
	nodeCreated(node, app) {
		if (node.comfyClass === "LoraList") {
            // Store all lora widgets
            const loraWidgets = [];
            // We need to keep track of which widgets are currently visible
            // But ComfyUI recreates widgets on reload.
            
            // Wait for widgets to be populated
            setTimeout(() => {
                if (!node.widgets) return;

                // Identify lora widgets
                const originalWidgets = [...node.widgets];
                node.widgets.length = 0; // Clear widgets

                // Separate lora widgets from others (if any)
                const otherWidgets = [];
                
                originalWidgets.forEach(w => {
                    if (w.name && w.name.startsWith("lora_")) {
                        loraWidgets.push(w);
                    } else {
                        otherWidgets.push(w);
                    }
                });

                // Sort lora widgets by index just in case
                loraWidgets.sort((a, b) => {
                    const idxA = parseInt(a.name.split("_")[1]);
                    const idxB = parseInt(b.name.split("_")[1]);
                    return idxA - idxB;
                });

                // Function to rebuild the widget list
                const updateWidgets = () => {
                    node.widgets = [...otherWidgets]; // Start with non-lora widgets
                    
                    // Add "Add Lora" button at the top or bottom? 
                    // Let's put it at the bottom of the list.
                    
                    // Add visible lora widgets
                    // A widget is visible if it has a value != "None" OR if it's the next available one we just added
                    // Actually, we should just maintain a "count" of visible widgets.
                    
                    // Determine how many to show
                    // We want to show all that have values, plus maybe one empty one if none are set?
                    // Or just show the ones the user added.
                    
                    // Let's count how many have values
                    let lastIndexWithVal = -1;
                    loraWidgets.forEach((w, i) => {
                        if (w.value && w.value !== "None") {
                            lastIndexWithVal = i;
                        }
                    });
                    
                    // We want to show up to lastIndexWithVal
                    // But the user might want to add more.
                    // We will use a property on the node to track "user desired count" if possible, 
                    // or just rely on the button incrementing a counter.
                    
                    if (!node.properties) node.properties = {};
                    if (node.properties.shown_count === undefined) {
                        node.properties.shown_count = lastIndexWithVal + 1;
                        if (node.properties.shown_count === 0) node.properties.shown_count = 1; // Start with 1
                    }

                    const count = node.properties.shown_count;
                    
                    for (let i = 0; i < count && i < loraWidgets.length; i++) {
                        node.widgets.push(loraWidgets[i]);
                    }
                    
                    // Add button
                    node.addWidget("button", "Add Lora", null, () => {
                        if (node.properties.shown_count < loraWidgets.length) {
                            node.properties.shown_count++;
                            updateWidgets();
                            node.setDirtyCanvas(true, true);
                        } else {
                            alert("Max 50 LoRAs reached.");
                        }
                    });
                    
                    // Add "Remove Last" button?
                    node.addWidget("button", "Remove Last", null, () => {
                        if (node.properties.shown_count > 1) {
                            // Reset value of the one being removed
                            const w = loraWidgets[node.properties.shown_count - 1];
                            w.value = "None";
                            
                            node.properties.shown_count--;
                            updateWidgets();
                            node.setDirtyCanvas(true, true);
                        }
                    });

                    node.onResize?.(node.size);
                    app.graph.setDirtyCanvas(true, true);
                };

                updateWidgets();
            }, 100);
		}
	}
});
