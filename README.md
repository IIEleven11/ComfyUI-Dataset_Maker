# ComfyUI Dataset Maker

This custom node pack allows you to automate the creation of datasets by generating images for a list of concepts, each with a specific LoRA.

## Nodes

### Dataset Concepts List
Input a list of concepts, one per line.
- **Output**: List of concepts.

### Dataset LoRA List
A dynamic node that allows you to select LoRAs from dropdowns. Right-click the node to add or remove LoRA slots. The LoRAs are mapped to concepts in order (top to bottom).
- **Right-click menu**: "Add LoRA" to add a new slot, "Remove Last LoRA" to remove the last slot.
- **Output**: List of LoRA names.

### Dataset Configuration
Configures the batch generation.
- **Inputs**: 
    - `concepts`: Connect from Concept List.
    - `lora_names`: Connect from LoRA List.
    - `images_per_concept`: Number of images to generate for each concept.
- **Outputs**:
    - `concepts_batch`: Expanded list of concepts (repeated `images_per_concept` times).
    - `lora_batch`: Expanded list of LoRA names.

### Apply LoRA Batch
Applies the specified LoRA for each item in the batch.
- **Inputs**:
    - `model`: Base model (from Load Checkpoint).
    - `clip`: Base CLIP (from Load Checkpoint).
    - `lora_batch`: Connect from Dataset Configuration.
- **Outputs**:
    - `MODEL`: List of models with LoRAs applied.
    - `CLIP`: List of CLIPs with LoRAs applied.

### Dataset Prompt Generator
Generates prompts by injecting the concept into a template.
- **Inputs**:
    - `concepts_batch`: Connect from Dataset Configuration.
    - `template`: String template, e.g., "photo of a {concept}, high quality".
- **Outputs**:
    - `STRING`: List of prompts.

### Save Dataset Image
Saves the generated images into folders named after the concepts.
- **Inputs**:
    - `images`: Connect from VAE Decode.
    - `concept_name`: Connect `concepts_batch` from Dataset Configuration.
    - `output_folder`: Path to save the dataset.

## Usage Flow

1.  Add **Dataset Concepts List** and write your concepts (one per line).
2.  Add **Dataset LoRA List**. Right-click and use "Add LoRA" to add as many LoRA slots as you have concepts. Select each LoRA from the dropdown - the order should match your concept list (top to bottom).
3.  Connect both to **Dataset Configuration**. Set `images_per_concept`.
4.  Load your Checkpoint. Connect Model and CLIP to **Apply LoRA Batch**.
5.  Connect `lora_batch` from **Dataset Configuration** to **Apply LoRA Batch**.
6.  Connect `concepts_batch` from **Dataset Configuration** to **Dataset Prompt Generator**. Set your prompt template.
7.  Connect `CLIP` (from Apply LoRA Batch) and `STRING` (from Prompt Generator) to a standard **CLIP Text Encode**.
8.  Connect `MODEL` (from Apply LoRA Batch) and `CONDITIONING` (from CLIP Text Encode) to **KSampler**.
9.  Connect `concepts_batch` from **Dataset Configuration** to **Save Dataset Image** (`concept_name` input).
10. Connect `IMAGE` (from VAE Decode) to **Save Dataset Image**.

When you queue the prompt, ComfyUI will execute the generation loop for every item in the batch, applying the correct LoRA and saving to the correct folder.
