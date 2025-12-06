import os
import folder_paths
import comfy.sd
import comfy.utils
import comfy.samplers
import numpy as np
from PIL import Image
import time
import itertools
import torch
from nodes import LoraLoader


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
    
    RETURN_TYPES = ("CONCEPT_LIST",)
    RETURN_NAMES = ("concepts",)
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, concepts_text):
        concepts = [line.strip() for line in concepts_text.splitlines() if line.strip()]
        return (concepts,)


class LoraList:
    """Dynamic LoRA selector node - add as many LoRAs as needed with the + button."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {},
            "optional": FlexibleOptionalInputType(any_type),
            "hidden": {}
        }
    
    RETURN_TYPES = ("LORA_LIST",)
    RETURN_NAMES = ("lora_names",)
    FUNCTION = "process"
    CATEGORY = "DatasetMaker"

    def process(self, **kwargs):
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
            
            if lora_name:
                loras.append(lora_name)
        
        return (loras,)


class DatasetGenerator:
    """Main dataset generation node - connects to standard SDXL workflow components."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "concepts": ("CONCEPT_LIST",),
                "lora_list": ("LORA_LIST",),
                "positive_template": ("STRING", {"multiline": True, "default": "photo of a person {concept}, high quality, detailed"}),
                "negative_prompt": ("STRING", {"multiline": True, "default": "bad quality, blurry, distorted"}),
                "images_per_concept": ("INT", {"default": 5, "min": 1, "max": 100}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 100}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 1.0, "max": 30.0, "step": 0.5}),
                "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "lora_strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.1}),
                "output_folder": ("STRING", {"default": "dataset_output"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    OUTPUT_NODE = True
    CATEGORY = "DatasetMaker"

    def generate(self, model, clip, vae, concepts, lora_list, positive_template, negative_prompt,
                 images_per_concept, width, height, seed, steps, cfg, sampler_name, scheduler, 
                 denoise, lora_strength, output_folder):
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Match loras to concepts
        if len(lora_list) == 0:
            lora_list = [""] * len(concepts)
        elif len(lora_list) < len(concepts):
            lora_list = list(itertools.islice(itertools.cycle(lora_list), len(concepts)))
        
        all_images = []
        current_seed = seed
        
        for concept_idx, (concept, lora_name) in enumerate(zip(concepts, lora_list)):
            print(f"DatasetMaker: Processing concept {concept_idx + 1}/{len(concepts)}: '{concept}' with lora: '{lora_name or 'None'}'")
            
            # Apply LoRA if specified
            work_model = model
            work_clip = clip
            
            if lora_name:
                lora_path = folder_paths.get_full_path("loras", lora_name)
                if lora_path:
                    try:
                        work_model, work_clip = LoraLoader().load_lora(
                            work_model, work_clip, lora_name, lora_strength, lora_strength
                        )
                        print(f"DatasetMaker: Loaded LoRA: {lora_name}")
                    except Exception as e:
                        print(f"DatasetMaker: Failed to load LoRA {lora_name}: {e}")
                else:
                    print(f"DatasetMaker: LoRA not found: {lora_name}")
            
            # Create positive prompt with concept
            positive_text = positive_template.replace("{concept}", concept)
            
            # Encode prompts
            pos_tokens = work_clip.tokenize(positive_text)
            pos_cond, pos_pooled = work_clip.encode_from_tokens(pos_tokens, return_pooled=True)
            positive_conditioning = [[pos_cond, {"pooled_output": pos_pooled}]]
            
            neg_tokens = work_clip.tokenize(negative_prompt)
            neg_cond, neg_pooled = work_clip.encode_from_tokens(neg_tokens, return_pooled=True)
            negative_conditioning = [[neg_cond, {"pooled_output": neg_pooled}]]
            
            # Create folder for this concept
            safe_concept = "".join([c for c in concept if c.isalpha() or c.isdigit() or c in " _-"]).strip()
            safe_concept = safe_concept.replace(" ", "_")
            concept_folder = os.path.join(output_folder, safe_concept)
            os.makedirs(concept_folder, exist_ok=True)
            
            # Generate images for this concept
            for img_idx in range(images_per_concept):
                print(f"DatasetMaker: Generating image {img_idx + 1}/{images_per_concept} for '{concept}'")
                
                # Create empty latent
                batch_size = 1
                latent = torch.zeros([batch_size, 4, height // 8, width // 8], device=comfy.model_management.intermediate_device())
                latent_image = {"samples": latent}
                
                # Prepare noise
                noise = comfy.sample.prepare_noise(latent_image["samples"], current_seed + img_idx)
                
                # Sample
                samples = comfy.sample.sample(
                    work_model, 
                    noise, 
                    steps, 
                    cfg, 
                    sampler_name, 
                    scheduler, 
                    positive_conditioning, 
                    negative_conditioning, 
                    latent_image["samples"],
                    denoise=denoise
                )
                
                # Decode
                decoded = vae.decode(samples)
                
                # Save image
                for i, image in enumerate(decoded):
                    img_array = 255. * image.cpu().numpy()
                    img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
                    
                    timestamp = int(time.time() * 1000)
                    filename = f"{safe_concept}_{img_idx:04d}_{timestamp}.png"
                    filepath = os.path.join(concept_folder, filename)
                    img.save(filepath)
                    print(f"DatasetMaker: Saved {filepath}")
                
                all_images.append(decoded)
            
            # Increment seed for next concept
            current_seed += images_per_concept
        
        # Combine all images
        if all_images:
            combined = torch.cat(all_images, dim=0)
            return (combined,)
        
        return (torch.zeros([1, height, width, 3]),)


class DatasetLoraLoader:
    """LoRA loader that outputs MODEL and CLIP for integration with standard workflows.
    Use this to preview a single concept before running the full dataset generation."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "lora_list": ("LORA_LIST",),
                "lora_index": ("INT", {"default": 0, "min": 0, "max": 100}),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.1}),
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.1}),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    FUNCTION = "load_lora"
    CATEGORY = "DatasetMaker"

    def load_lora(self, model, clip, lora_list, lora_index, strength_model, strength_clip):
        if not lora_list or lora_index >= len(lora_list):
            return (model, clip)
        
        lora_name = lora_list[lora_index]
        if not lora_name or lora_name == "None":
            return (model, clip)
        
        lora_path = folder_paths.get_full_path("loras", lora_name)
        if lora_path is None:
            print(f"DatasetMaker: LoRA not found: {lora_name}")
            return (model, clip)
        
        try:
            model, clip = LoraLoader().load_lora(model, clip, lora_name, strength_model, strength_clip)
            print(f"DatasetMaker: Loaded LoRA: {lora_name}")
        except Exception as e:
            print(f"DatasetMaker: Error loading LoRA {lora_name}: {e}")
        
        return (model, clip)


class DatasetPromptBuilder:
    """Builds a prompt from a concept list. Use to preview a single concept."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "concepts": ("CONCEPT_LIST",),
                "concept_index": ("INT", {"default": 0, "min": 0, "max": 100}),
                "template": ("STRING", {"multiline": True, "default": "photo of a person {concept}, high quality"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "build"
    CATEGORY = "DatasetMaker"

    def build(self, concepts, concept_index, template):
        if not concepts or concept_index >= len(concepts):
            return (template,)
        
        concept = concepts[concept_index]
        prompt = template.replace("{concept}", concept)
        return (prompt,)


NODE_CLASS_MAPPINGS = {
    "ConceptList": ConceptList,
    "LoraList": LoraList,
    "DatasetGenerator": DatasetGenerator,
    "DatasetLoraLoader": DatasetLoraLoader,
    "DatasetPromptBuilder": DatasetPromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ConceptList": "Dataset Concepts List",
    "LoraList": "Dataset LoRA List",
    "DatasetGenerator": "Dataset Generator",
    "DatasetLoraLoader": "Dataset LoRA Loader (Preview)",
    "DatasetPromptBuilder": "Dataset Prompt Builder (Preview)",
}
