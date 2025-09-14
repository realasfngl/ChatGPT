# ChatGPT Reverse

A reverse-engineered implementation of ChatGPT that bypasses OpenAI's API system. This project provides free access to ChatGPT as API by emulating browser behavior and solving OpenAI Turnstile challenge through VM decompilation.

## Quick Start

**Install dependencies:**
```bash
pip install fastapi uvicorn curl-cffi pydantic pillow colorama esprima tzdata
```

**Run the API server:**
```bash
python api_server.py
```

The server runs on `http://localhost:6969`

**Or test directly:**
```bash
python manual.py
```

## Usage

### API Endpoint

POST `/conversation`

Request:
```json
{
    "proxy": "http://user:pass@ip:port",
    "message": "Your message here",
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

The image field accepts base64-encoded images with data URI format. The system automatically handles image upload, processing, and attachment to the conversation.

Response:
```json
{
    "status": "success", 
    "result": "ChatGPT response"
}
```

### Direct Usage

```python
from wrapper import ChatGPT

client = ChatGPT("http://user:pass@proxy:port")
response = client.ask_question("Hello")
print(response)

# With image
response = client.ask_question("What's in this image?", "data:image/png;base64,...")
```
![alt text](images/image.png)

## Request Flow and Authentication

The system makes several authenticated requests to ChatGPT endpoints:

### 1. Initial Requirements (`/backend-anon/sentinel/chat-requirements`)
- Sends VM token in request body as `p` parameter
- Receives chat requirements token, proof-of-work challenge, and Turnstile bytecode
- Headers: `oai-client-version`, `oai-device-id`

### 2. Conduit Token (`/backend-anon/f/conversation/prepare`)
- Prepares conversation context
- Uses `x-conduit-token: no-token` header initially
- Returns conduit token for actual conversation

### 3. Main Conversation (`/backend-anon/f/conversation`)
- **Critical headers with VM components:**
  - `openai-sentinel-chat-requirements-token`: From requirements endpoint
  - `openai-sentinel-proof-token`: Solved proof-of-work challenge
  - `openai-sentinel-turnstile-token`: **VM-generated Turnstile token**
  - `x-conduit-token`: From conduit preparation
  - `oai-echo-logs`: Timing data for behavioral analysis


## VM and Turnstile Token System

The core of this implementation is the VM system that solves OpenAI Turnstile challenges used in the `openai-sentinel-turnstile-token` header.

### How It Works

ChatGPT uses Turnstile anti-bot protection that sends encrypted JavaScript bytecode to verify legitimate browsers. Our system:

1. **Receives bytecode** from ChatGPT servers in the requirements response
2. **Decompiles bytecode** into readable JavaScript operations  
3. **Parses decompiled output** to extract variable assignments and XOR keys
4. **Executes VM logic** by building browser fingerprint payload with XOR encryption

### Decompiler

The decompiler (`wrapper/reverse/decompiler.py`) translates Turnstile's custom bytecode:

```python
mapping = {
        "1": "XOR_STR",
        "2": "SET_VALUE",
        "3": "BTOA",
        "4": "BTOA_2",
        "5": "ADD_OR_PUSH",
        "6": "ARRAY_ACCESS",
        "7": "CALL",
        "8": "COPY",
        "10": "window",
        "11": "GET_SCRIPT_SRC",
        "12": "GET_MAP",
        "13": "TRY_CALL",
        "14": "JSON_PARSE",
        "15": "JSON_STRINGIFY",
        "17": "CALL_AND_SET",
        "18": "ATOB",
        "19": "BTOA_3",
        "20": "IF_EQUAL_CALL",
        "21": "IF_DIFF_CALL",
        "22": "TEMP_STACK_CALL",
        "23": "IF_DEFINED_CALL",
        "24": "BIND_METHOD",
        "27": "REMOVE_OR_SUBTRACT",
        "28": "undefined",
        "25": "undefined",
        "26": "undefined",
        "29": "LESS_THAN",
        "31": "INCREMENT",
        "32": "DECREMENT_AND_EXEC",
        "33": "MULTIPLY"
    }
```

It handles:
- Multi-layer bytecode decryption using XOR operations
- Variable state tracking across operations
- Browser API simulation (window, document objects)
- Three-stage decompilation process with nested encrypted layers

Also check decompiled.js for the full decompiled VM output.

![alt text](images/image-1.png)

### VM Execution

The VM (`wrapper/reverse/vm.py`) parses the decompiled output and extracts:

- **XOR encryption keys**: Dynamic keys for payload encryption extracted from `XOR_STR()` patterns
- **Variable assignments**: Browser fingerprint data collection points
- **Operation sequences**: DOM manipulation and measurement operations

Looking at the decompiled code, the VM identifies patterns like:
- `XOR_STR()` calls with different variables for encryption
- `getBoundingClientRect()` for element measurements  
- `navigator` property access for hardware fingerprints
- `localStorage.keys()` for browser storage data
- `Math.random()` calls requiring XOR self-encryption
- Performance timing measurements

The VM then builds the payload by providing realistic values:
- **Element measurements**: Realistic `getBoundingClientRect()` values
- **Navigator data**: Chrome browser fingerprints (`["Google Inc.","Win32",8,0]`)
- **Location info**: Current page URL and IP geolocation data
- **Storage keys**: Realistic localStorage key patterns
- **Random values**: Self-XOR encrypted random numbers

![alt text](images/image-2.png)

### Proof-of-Work Challenge

In addition to Turnstile, the system solves computational proof-of-work challenges:

```python
def solve_pow(seed, difficulty, config):
    for i in range(500000):
        result = runCheck(seed, difficulty, i, config)
        if result:
            return f"gAAAAAB{result}"
```

The PoW solver:
- Brute forces hash computations until difficulty threshold is met
- Uses FNV-1a hash algorithm with specific bit operations
- Integrates browser configuration data into the solution
- Provides the `openai-sentinel-proof-token` header value

### Challenge Integration

All challenge solutions work together:
1. **VM Token**: Generated from initial config, sent to `/chat-requirements`
2. **PoW Solution**: Computed from returned challenge, proves computational work
3. **Turnstile Token**: VM-generated from bytecode, proves browser legitimacy
4. **Conduit Token**: Session-specific token for conversation context

![alt text](images/image-3.png)

## Image Processing

The system handles image uploads through a multi-step process:

1. **Image Upload** (`/backend-anon/files`):
   - Accepts base64 image data
   - Returns file ID and Azure blob upload URL

2. **Blob Upload**: 
   - Uploads raw image data to Azure storage
   - Uses specific headers: `x-ms-blob-type: BlockBlob`

3. **Processing** (`/backend-anon/files/process_upload_stream`):
   - Processes uploaded image for multimodal use
   - Returns confirmation when ready

4. **Conversation Integration**:
   - References uploaded image via `file-service://{file_id}`
   - Includes image metadata (dimensions, mime type)

## Security Bypasses

**IP Detection**: Uses proxy rotation to avoid rate limits and geographic restrictions
**Browser Fingerprinting**: Emulates Chrome 139 with consistent headers and device properties
**Device Tracking**: Maintains stable device IDs (`oai-did`) across sessions  
**Behavioral Analysis**: Simulates realistic timing patterns in `oai-echo-logs`
**Challenge Solving**: Passes all cryptographic and computational verification steps

## Configuration

Proxy format: `http://username:password@host:port`

![alt text](images/image-4.png)

## Troubleshooting

**"Unusual activity" error**: Your IP is flagged, use a different proxy
**Requirements token fails**: VM token generation issue, check decompiler mappings  
**Turnstile token invalid**: Bytecode format changed, update operation mappings
**PoW challenge timeout**: Increase iteration limit or check hash implementation
**Image upload fails**: Check file size limits and blob storage connectivity

## Disclaimer

This project is for educational purposes only. If OpenAI has an Issue with this Project please contact me via my email nuhuh3116@gmail.com.
