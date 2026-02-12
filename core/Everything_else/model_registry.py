import os
import gc
import yaml
import time
import base64
from llama_cpp import Llama
from llama_cpp.llama_chat_format import MoondreamChatHandler
from core.paths import MODELS_DIR

# --- 1. CORE UTILITIES ---

def get_model_config(model_id):
    """Safely retrieves model settings from the YAML config."""
    config_path = os.path.join(MODELS_DIR, "models.yaml")
    try:
        with open(config_path, "r") as f:
            all_configs = yaml.safe_load(f).get("models", {})
        if model_id not in all_configs:
            raise ValueError(f"Model '{model_id}' not found in {config_path}")
        return all_configs[model_id]
    except Exception as e:
        print(f"[Jynx] Config Error: {e}")
        return {}

def get_stop_sequence(model_id):
    return ["</s>", "User:", "Assistant:"]

def encode_image(image_path):
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"[Jynx] Image error: {e}")
        return None

# --- 2. LIFECYCLE MANAGEMENT ---

ACTIVE_LLM = None

def unload_previous_model():
    global ACTIVE_LLM
    if ACTIVE_LLM is not None:
        try:
            ACTIVE_LLM.close()
        except: pass
        ACTIVE_LLM = None
    gc.collect()
    time.sleep(0.1)

# --- 3. THE LOADER ---

def load_model_from_config(model_id):
    global ACTIVE_LLM
    config = get_model_config(model_id)
    if not config:
        raise RuntimeError(f"Could not load config for {model_id}")

    model_path = os.path.join(MODELS_DIR, config["path"])
    clip_path = config.get("clip_path")
    abs_clip_path = os.path.join(MODELS_DIR, clip_path) if clip_path else None
    
    unload_previous_model()

    # Use specialized Moondream handler if it's a vision model
    chat_handler = MoondreamChatHandler(clip_model_path=abs_clip_path) if abs_clip_path else None

    try:
        # Pull context from config
        n_ctx = config.get("max_tokens", 4096)
        
        llm = Llama(
            model_path=model_path,
            chat_handler=chat_handler, 
            n_ctx=n_ctx,
            n_gpu_layers=config.get("n_gpu_layers", -1),
            verbose=False
        )
        ACTIVE_LLM = llm
        
        def call(prompt, stream_override=None, image_path=None, **kwargs):
            stream = config.get("stream", True) if stream_override is None else stream_override
            # Get max_tokens from kwargs (passed by council) or fallback to config
            m_tokens = kwargs.get("max_tokens", config.get("max_tokens", 512))
    
            if image_path and abs_clip_path:
                b64_data = encode_image(image_path)
                if b64_data:
                    response = llm.create_chat_completion(
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"}}
                        ]}],
                        stream=stream,
                        max_tokens=m_tokens
                    )

                    if stream:
                        def text_generator():
                            for chunk in response:
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    content = chunk['choices'][0].get('delta', {}).get('content', '')
                                    if content: yield content
                        return text_generator()
                    return response['choices'][0]['message']['content']

            # Standard text inference logic
            return llm(
                prompt=f"User: {prompt}\nAssistant:", 
                stream=stream, 
                stop=get_stop_sequence(model_id),
                max_tokens=m_tokens
            )

        return call, config
    except Exception as e:
        print(f"[Jynx] Launch Failed for {model_id}: {e}")
        raise

def get_visual_description(image_path):
    """Helper for internal description requests."""
    try:
        vision_fn, _ = load_model_from_config("jynx_vision")
        return vision_fn("Describe this image.", image_path=image_path, stream_override=False)
    except Exception as e:
        return f"Vision Error: {e}"