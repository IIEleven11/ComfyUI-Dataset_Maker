import os
import folder_paths
import comfy.sd
import comfy.utils
import numpy as np
from PIL import Image
import time
import itertools

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
    @classmethod
    def INPUT_TYPES(s):
        lora_list = ["None"] + folder_paths.get_filename_list("loras")
        inputs = {
            "required": {
                "lora_count": ("INT", {"default": 1, "min": 1, "max": 50, "step": 1}),
            },
            "optional": {}
        }
        for i in range(1, 51):
            inputs["optional"][f"lora_{i}"] = (lora_list,)
        return inputs
    
    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("lora_names",)
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, lora_count, **kwargs):
        loras = []
        for i in range(1, 51):
            key = f"lora_{i}"
            lora_name = kwargs.get(key, "None")
            if lora_name == "None":
                lora_name = ""
            loras.append(lora_name)
            
        return (loras[:lora_count],)

class DatasetConfig:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "concepts": ("LIST",),
                "lora_names": ("LIST",),
                "images_per_concept": ("INT", {"default": 1, "min": 1, "max": 1000}),
            }
        }
    
    RETURN_TYPES = ("LIST", "LIST")
    RETURN_NAMES = ("concepts_batch", "lora_batch")
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, concepts, lora_names, images_per_concept):
        # Handle mismatch
        if len(lora_names) == 0:
             lora_names = [""] * len(concepts)
        elif len(lora_names) < len(concepts):
            # Cycle loras to match concepts length
            lora_names = list(itertools.islice(itertools.cycle(lora_names), len(concepts)))
        
        concepts_batch = []
        lora_batch = []
        
        for i in range(len(concepts)):
            c = concepts[i]
            l = lora_names[i]
            for _ in range(images_per_concept):
                concepts_batch.append(c)
                lora_batch.append(l)
                
        return (concepts_batch, lora_batch)

class ApplyLoraBatch:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "lora_batch": ("LIST",),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, model, clip, lora_batch):
        out_models = []
        out_clips = []
        
        for lora_name in lora_batch:
            if not lora_name:
                out_models.append(model)
                out_clips.append(clip)
                continue

            lora_path = folder_paths.get_full_path("loras", lora_name)
            if lora_path is None:
                print(f"DatasetMaker: Lora not found: {lora_name}")
                out_models.append(model)
                out_clips.append(clip)
                continue
                
            try:
                m, c = comfy.sd.load_lora_for_models(model, clip, lora_path, 1.0, 1.0)
                out_models.append(m)
                out_clips.append(c)
            except Exception as e:
                print(f"DatasetMaker: Error loading lora {lora_name}: {e}")
                out_models.append(model)
                out_clips.append(clip)
            
        return (out_models, out_clips)

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
    "DatasetConfig": DatasetConfig,
    "ApplyLoraBatch": ApplyLoraBatch,
    "PromptBatch": PromptBatch,
    "SaveDatasetImage": SaveDatasetImage
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptList": "Dataset Concepts List",
    "LoraList": "Dataset LoRA List",
    "DatasetConfig": "Dataset Configuration",
    "ApplyLoraBatch": "Apply LoRA Batch",
    "PromptBatch": "Dataset Prompt Generator",
    "SaveDatasetImage": "Save Dataset Image"
}
