import os
import folder_paths
import comfy.sd
import comfy.utils
import numpy as np
from PIL import Image
import time
import itertools


class AnyType(str):
    """A special class that is always equal in not equal comparisons."""
    def __ne__(self, __value: object) -> bool:
        return False


class FlexibleOptionalInputType(dict):
    """A special class to make flexible nodes that accept dynamic inputs."""

    def __init__(self, type):
        self.type = type

    def __getitem__(self, key):
        return (self.type,)

    def __contains__(self, key):
        return True


any_type = AnyType("*")


class ConceptList:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"concepts_text": ("STRING", {"multiline": True, "default": "concept1\nconcept2"})}}
    
    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("concepts",)
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, concepts_text):
        concepts = [line.strip() for line in concepts_text.splitlines() if line.strip()]
        return (concepts,)

class LoraList:
    """Dynamic LoRA selector node that applies LoRAs to a batch of concepts."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "concepts": ("LIST",),
                "images_per_concept": ("INT", {"default": 1, "min": 1, "max": 1000}),
            },
            "optional": FlexibleOptionalInputType(any_type),
            "hidden": {}
        }
    
    RETURN_TYPES = ("MODEL", "CLIP", "LIST")
    RETURN_NAMES = ("model", "clip", "concepts_batch")
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, model, clip, concepts, images_per_concept, **kwargs):
        # 1. Extract LoRAs
        loras = []
        # Sort by lora_1, lora_2, etc to maintain order
        lora_keys = sorted([k for k in kwargs.keys() if k.startswith("lora_")], 
                          key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 0)
        
        for key in lora_keys:
            value = kwargs[key]
            # Handle both simple string values and dict values (like power lora loader)
            if isinstance(value, dict):
                lora_name = value.get("lora", "")
            else:
                lora_name = value if value and value != "None" else ""
            
            # We keep empty strings to maintain alignment with concepts if user selected "None"
            loras.append(lora_name)

        # 2. Align LoRAs with Concepts
        # If fewer LoRAs than concepts, cycle them? Or pad with None?
        # Requirement: "Each concept would use a specific lora."
        # Assuming user provides LoRAs in order.
        
        if len(loras) < len(concepts):
            # Pad with empty strings (no LoRA)
            loras.extend([""] * (len(concepts) - len(loras)))
        elif len(loras) > len(concepts):
            # Truncate
            loras = loras[:len(concepts)]
            
        # 3. Create Batch
        out_models = []
        out_clips = []
        concepts_batch = []
        
        for i in range(len(concepts)):
            concept = concepts[i]
            lora_name = loras[i]
            
            # Prepare the model/clip for this concept
            current_model = model
            current_clip = clip
            
            if lora_name:
                lora_path = folder_paths.get_full_path("loras", lora_name)
                if lora_path:
                    try:
                        current_model, current_clip = comfy.sd.load_lora_for_models(model, clip, lora_path, 1.0, 1.0)
                    except Exception as e:
                        print(f"DatasetMaker: Error loading lora {lora_name}: {e}")
                else:
                    print(f"DatasetMaker: Lora not found: {lora_name}")
            
            # Add to batch N times
            for _ in range(images_per_concept):
                out_models.append(current_model)
                out_clips.append(current_clip)
                concepts_batch.append(concept)
                
        return (out_models, out_clips, concepts_batch)



class PromptBatch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "concepts_batch": ("LIST",),
                "template": ("STRING", {"multiline": True, "default": "photo of a {concept}"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, concepts_batch, template):
        prompts = []
        for c in concepts_batch:
            prompts.append(template.replace("{concept}", c))
        return (prompts,)

class SaveDatasetImage:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "concept_name": ("STRING", {"forceInput": True}),
                "output_folder": ("STRING", {"default": "dataset_output"}),
            }
        }
    
    RETURN_TYPES = ()
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "DatasetMaker"

    def save(self, images, concept_name, output_folder):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)
            
        # Sanitize concept name for folder
        safe_concept = "".join([c for c in concept_name if c.isalpha() or c.isdigit() or c in " _-"]).strip()
        concept_folder = os.path.join(output_folder, safe_concept)
        
        if not os.path.exists(concept_folder):
            os.makedirs(concept_folder, exist_ok=True)
            
        for i, image in enumerate(images):
            img_array = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
            
            timestamp = int(time.time() * 1000)
            filename = f"{safe_concept}_{timestamp}_{i}.png"
            img.save(os.path.join(concept_folder, filename))
            
        return {}

NODE_CLASS_MAPPINGS = {
    "ConceptList": ConceptList,
    "LoraList": LoraList,
    "PromptBatch": PromptBatch,
    "SaveDatasetImage": SaveDatasetImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptList": "Dataset Concepts List",
    "LoraList": "Dataset LoRA Loader",
    "PromptBatch": "Dataset Prompt Generator",
    "SaveDatasetImage": "Save Dataset Image"
}
