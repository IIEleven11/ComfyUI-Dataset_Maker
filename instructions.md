# ComfyUI-Dataset_maker

## Task: Create the comfyui nodes that would allow me to provide a list of concepts. Each concept would be used to generate multiple images using a text to image model. The images would be saved to a folder named after the concept. Each concept would use a specific lora. So lora loading per concept should be automated. 

- End User Flow:
    1. First they write down in a node, one per line, each concept. 
        Example: facing forward
                 sitting down
                 running
    2. Next in a new node we need to set each lora. These should be loaded from the ComfyUI/models/Lora folder. The user should be able to select which lora corresponds to which concept.
    3. Then the user sets the number of images to generate per concept in a new node.
    4. We can use existing load checkpoint, clip text encode, ksampler, and vae encode nodes where needed.
    5. Finally, the user sets the output folder where all the concept folders will be created and images saved.


