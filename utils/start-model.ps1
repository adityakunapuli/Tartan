llama-server -m "A:\models\Qwen2.5-Coder-32B-Instruct-IQ3_XS.gguf" `
  -ngl 99 `
  -ts 1,1 `
  -sm layer `
  -c 8192 `
  -fa on `
  -ctk q8_0 -ctv q8_0