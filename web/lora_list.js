import { app } from "../../scripts/app.js";

const LORA_LIST_NODE_TYPE = "LoraList";

// Cache for LoRA list
let cachedLoraList = null;

async function getLoraList() {
    if (cachedLoraList) {
        return cachedLoraList;
    }
    try {
        const response = await fetch("/object_info/LoraLoader");
        if (response.ok) {
            const data = await response.json();
            if (data.LoraLoader?.input?.required?.lora_name?.[0]) {
                cachedLoraList = data.LoraLoader.input.required.lora_name[0];
                return cachedLoraList;
            }
        }
    } catch (e) {
        console.error("DatasetMaker: Failed to fetch LoRA list", e);
    }
    return [];
}

app.registerExtension({
    name: "DatasetMaker.LoraList",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== LORA_LIST_NODE_TYPE) {
            return;
        }
        
        // Pre-fetch LoRA list
        getLoraList();
        
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = async function() {
            const result = onNodeCreated?.apply(this, arguments);
            
            // Add initial LoRA slot
            await this.addLoraInput();
            
            return result;
        };
        
        // Add a LoRA input slot
        nodeType.prototype.addLoraInput = async function() {
            const loraWidgets = this.widgets?.filter(w => w.name.startsWith("lora_")) || [];
            const newIndex = loraWidgets.length + 1;
            const inputName = `lora_${newIndex}`;
            
            // Get available LoRAs
            const loraList = await getLoraList();
            const loras = ["None", ...loraList];
            
            // Add widget for LoRA selection
            const widget = this.addWidget("combo", inputName, "None", (value) => {
                // Callback when value changes
            }, { values: loras });
            
            widget.loraIndex = newIndex;
            
            this.setSize(this.computeSize());
            return widget;
        };
        
        // Remove the last LoRA input
        nodeType.prototype.removeLastLoraInput = function() {
            const loraWidgets = this.widgets?.filter(w => w.name.startsWith("lora_")) || [];
            if (loraWidgets.length > 1) {
                const lastWidget = loraWidgets[loraWidgets.length - 1];
                const widgetIndex = this.widgets.indexOf(lastWidget);
                if (widgetIndex > -1) {
                    this.widgets.splice(widgetIndex, 1);
                    this.setSize(this.computeSize());
                }
            }
        };
        
        // Override getExtraMenuOptions to add Add/Remove LoRA options
        const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
        nodeType.prototype.getExtraMenuOptions = function(_, options) {
            getExtraMenuOptions?.apply(this, arguments);
            
            options.unshift(
                {
                    content: "Add LoRA",
                    callback: () => {
                        this.addLoraInput();
                    }
                },
                {
                    content: "Remove Last LoRA",
                    callback: () => {
                        this.removeLastLoraInput();
                    }
                },
                null // separator
            );
        };
        
        // Serialize the node to save LoRA selections
        const onSerialize = nodeType.prototype.onSerialize;
        nodeType.prototype.onSerialize = function(o) {
            onSerialize?.apply(this, arguments);
            
            o.lora_values = {};
            const loraWidgets = this.widgets?.filter(w => w.name.startsWith("lora_")) || [];
            for (const widget of loraWidgets) {
                o.lora_values[widget.name] = widget.value;
            }
        };
        
        // Configure the node when loaded
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function(info) {
            onConfigure?.apply(this, arguments);
            
            if (info.lora_values) {
                // Remove existing LoRA widgets
                this.widgets = this.widgets?.filter(w => !w.name.startsWith("lora_")) || [];
                
                // Recreate LoRA widgets from saved data
                const loraKeys = Object.keys(info.lora_values).sort((a, b) => {
                    const numA = parseInt(a.split("_")[1]) || 0;
                    const numB = parseInt(b.split("_")[1]) || 0;
                    return numA - numB;
                });
                
                for (const key of loraKeys) {
                    this.addLoraInput().then(widget => {
                        if (widget) {
                            widget.value = info.lora_values[key];
                        }
                    });
                }
            }
        };
    }
});
