import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Cache for lora list
let loraListCache = null;

async function getLoras() {
    if (loraListCache) {
        return loraListCache;
    }
    try {
        const resp = await api.fetchApi("/object_info/LoraLoader");
        const data = await resp.json();
        if (data?.LoraLoader?.input?.required?.lora_name?.[0]) {
            loraListCache = data.LoraLoader.input.required.lora_name[0];
            return loraListCache;
        }
    } catch (e) {
        console.error("DatasetMaker: Failed to fetch lora list", e);
    }
    return [];
}

app.registerExtension({
    name: "DatasetMaker.LoraList",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "LoraList") {
            return;
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const result = onNodeCreated?.apply(this, arguments);
            
            this.loraCounter = 0;
            this.serialize_widgets = true;
            
            // Add the "Add Lora" button
            this.addWidget("button", "➕ Add LoRA", null, () => {
                this.addLoraWidget();
            });
            
            return result;
        };

        nodeType.prototype.addLoraWidget = async function(loraName = null) {
            this.loraCounter++;
            const widgetName = `lora_${this.loraCounter}`;
            
            const loras = await getLoras();
            const loraOptions = ["None", ...loras];
            
            const widget = this.addWidget("combo", widgetName, loraName || "None", (v) => {
                // Value changed callback
            }, { values: loraOptions });
            
            // Move button to end
            const buttonWidget = this.widgets.find(w => w.type === "button");
            if (buttonWidget) {
                const buttonIndex = this.widgets.indexOf(buttonWidget);
                const widgetIndex = this.widgets.indexOf(widget);
                if (widgetIndex < buttonIndex) {
                    // Widget is already before button, good
                } else {
                    // Move widget before button
                    this.widgets.splice(widgetIndex, 1);
                    this.widgets.splice(buttonIndex, 0, widget);
                }
            }
            
            // Resize node to fit
            const sz = this.computeSize();
            this.size[0] = Math.max(this.size[0], sz[0]);
            this.size[1] = Math.max(this.size[1], sz[1]);
            
            this.setDirtyCanvas(true, true);
            return widget;
        };

        nodeType.prototype.removeLoraWidget = function(widgetName) {
            const widgetIndex = this.widgets.findIndex(w => w.name === widgetName);
            if (widgetIndex !== -1) {
                this.widgets.splice(widgetIndex, 1);
                this.setDirtyCanvas(true, true);
            }
        };

        // Handle right-click menu on lora widgets
        const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function(_, options) {
            getExtraMenuOptions?.apply(this, arguments);
            
            // Find which widget is being right-clicked
            const canvas = app.canvas;
            const pos = canvas.graph_mouse;
            const nodePos = this.pos;
            const relY = pos[1] - nodePos[1];
            
            let targetWidget = null;
            let currentY = 0;
            for (const widget of this.widgets) {
                if (widget.name?.startsWith("lora_")) {
                    const widgetHeight = LiteGraph.NODE_WIDGET_HEIGHT || 20;
                    if (relY >= currentY && relY < currentY + widgetHeight + 4) {
                        targetWidget = widget;
                        break;
                    }
                }
                currentY += (LiteGraph.NODE_WIDGET_HEIGHT || 20) + 4;
            }
            
            if (targetWidget) {
                options.unshift(
                    {
                        content: `🗑️ Remove ${targetWidget.name}`,
                        callback: () => {
                            this.removeLoraWidget(targetWidget.name);
                        }
                    },
                    null // separator
                );
            }
        };

        // Serialize: Save widget values
        const onSerialize = nodeType.prototype.onSerialize;
        nodeType.prototype.onSerialize = function(o) {
            onSerialize?.apply(this, arguments);
            
            o.loraCounter = this.loraCounter;
            o.loraWidgets = [];
            
            for (const widget of this.widgets) {
                if (widget.name?.startsWith("lora_")) {
                    o.loraWidgets.push({
                        name: widget.name,
                        value: widget.value
                    });
                }
            }
        };

        // Deserialize: Restore widget values
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function(o) {
            // Remove existing lora widgets first
            this.widgets = this.widgets?.filter(w => !w.name?.startsWith("lora_")) || [];
            this.loraCounter = o.loraCounter || 0;
            
            onConfigure?.apply(this, arguments);
            
            // Restore lora widgets
            if (o.loraWidgets) {
                for (const loraData of o.loraWidgets) {
                    this.addLoraWidget(loraData.value);
                }
            }
        };
    }
});
