# ComfyUI Dataset Maker

This custom node pack allows you to automate the creation of datasets by generating images for a list of concepts, each with a specific LoRA.

## Nodes

### Dataset Concepts List
Input a list of concepts, one per line.
- **Output**: List of concepts.

### Dataset LoRA List
Input a list of LoRA filenames, one per line. These should correspond to the concepts in the Concept List.
- **Output**: List of LoRA names.

### Get Available LoRAs
Helper node that outputs a list of all available LoRAs in your `models/loras` folder as a string. You can copy-paste from this list to the LoRA List node.

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

1.  Add **Dataset Concepts List** and write your concepts.
2.  Add **Dataset LoRA List** and write the corresponding LoRA filenames.
3.  Connect both to **Dataset Configuration**. Set `images_per_concept`.
4.  Load your Checkpoint. Connect Model and CLIP to **Apply LoRA Batch**.
5.  Connect `lora_batch` from **Dataset Configuration** to **Apply LoRA Batch**.
6.  Connect `concepts_batch` from **Dataset Configuration** to **Dataset Prompt Generator**. Set your prompt template.
7.  Connect `CLIP` (from Apply LoRA Batch) and `STRING` (from Prompt Generator) to a standard **CLIP Text Encode**.
8.  Connect `MODEL` (from Apply LoRA Batch) and `CONDITIONING` (from CLIP Text Encode) to **KSampler**.
9.  Connect `concepts_batch` from **Dataset Configuration** to **Save Dataset Image** (`concept_name` input).
10. Connect `IMAGE` (from VAE Decode) to **Save Dataset Image**.

When you queue the prompt, ComfyUI will execute the generation loop for every item in the batch, applying the correct LoRA and saving to the correct folder.
