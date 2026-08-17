# AI Customer Inbox Agent

## What is this project?

This project is an **AI-powered customer service assistant**. Think of it as a digital employee that can automatically answer common questions from your customers 24/7. It's designed to work across different communication channels like your website's chat, WhatsApp, and email. When a customer asks a question, the AI reads it, finds the answer from your business information, and responds. If the customer seems interested in buying your products or services, the AI captures this as a "sales lead" and notifies your sales team.

## Project Structure

Understanding the files and folders in this project helps you know where to make changes.

```
project1_AI_customer_inbox_agent/
├── .env.example          # Template for environment variables (API keys, settings)
├── .gitignore            # Defines which files Git should ignore
├── README.md             # This file
├── Dockerfile            # Instructions for Docker to build an image
├── docker-compose.yml    # Configuration for Docker Compose to run the app
├── requirements.txt      # List of Python libraries needed to run the project
├── app/                  # Main application code
│   ├── __init__.py       # Makes 'app' a Python package
│   ├── main.py           # Defines the web routes (endpoints like /chat, /webhook/whatsapp)
│   ├── agent.py          # Core logic: classify, retrieve, respond, capture lead
│   ├── llm_client.py     # Handles communication with OpenAI/Claude/Gemini APIs
│   ├── retrieval.py      # Searches your knowledge base files for answers
│   ├── notify.py         # Logic for notifying salespeople about new leads
│   ├── models.py         # Defines database tables (Conversations, Messages, Leads)
│   ├── database.py       # Handles database connections
│   └── config.py         # Loads settings from .env file
├── data/                 # Your business information
│   ├── business_profile.json  # General business details (name, hours, location)
│   └── knowledge_base/        # Your FAQ files (Markdown format)
│       ├── booking_and_process.md
│       ├── pricing_and_delivery.md
│       └── warranty_and_maintenance.md
├── static/               # Files for the web frontend (HTML, CSS, JS)
│   └── index.html        # The chat interface displayed at http://127.0.0.1:8000
└── tests/                # Automated tests
    └── test_core.py      # Tests for the main agent workflow
```

## Project Architecture

Images here that show the system with components like:
- User interface (web/WhatsApp/email)
- Message processing pipeline
- LLM integration
- Knowledge base
- Lead notification system

 ![web view](nexus1.png) 

## Why is it useful?

- **Saves Time**: Your human staff doesn't have to repeatedly answer the same questions like "Are you open on Sundays?" or "How much does installation cost?" The AI handles these.
- **Always Available**: Provides instant answers to customers, even outside of business hours.
- **Captures Leads**: Automatically identifies potential buyers and alerts your sales team.
- **Works Everywhere**: Can manage conversations from your website, WhatsApp, and email in one place.

## How does it work? (Simple Explanation)

1.  **Customer Asks**: A customer sends a message via web chat, WhatsApp, or email.
2.  **AI Reads**: The AI agent reads the message.
3.  **Finds Answer**: It searches a knowledge base (like a simple FAQ file you provide) to find the best answer.
4.  **Replies**: It writes a helpful reply and sends it back to the customer.
5.  **Checks Interest**: While replying, it also checks if the customer seems interested in buying. If so, it records this as a new sales lead.
6.  **Notifies**: It can send an alert (like an email or log message) to your sales team about the new lead.

## Getting Started (For Beginners)

To run this project, you'll need to install a few things on your computer. Don't worry, it's easier than it sounds!

### Prerequisites (What you need first)

- **Python**: This project is built with Python. You need to install Python (version 3.8 or newer) on your computer. You can download it from [python.org](https://www.python.org/downloads/).
- **API Key (Choose One)**: The AI needs to be powered by a large language model. You need an account and an API key from one of these providers:
    - **OpenAI** (for GPT models): Sign up at [platform.openai.com](https://platform.openai.com/signup) and create an API key.
    - **Anthropic** (for Claude models): Sign up and get an API key.
    - **Google** (for Gemini models): Sign up at [ai.google.dev](https://ai.google.dev/) and get an API key.

### Managing API Keys and Environment Variables (Security Guidelines)

API keys are like passwords for your AI account. Keeping them secure is critical.

- **Never Commit `.env`**: The `.env` file is automatically excluded from Git by the `.gitignore` file. This is crucial. **Never share your `.env` file or commit it to a public code repository.**
- **Unique Keys**: Use a unique API key just for this project if your provider allows it. This makes it easier to revoke if needed.
- **Environment Variable Best Practices**:
    - Store API keys only in the `.env` file.
    - Load them into your application using `os.getenv()` (as done in `app/config.py`). The application code correctly retrieves keys this way.
    - Do not hard-code API keys directly into Python files (e.g., `api_key = "sk-..."`).
- **Secure Storage**: Store your `.env` file in a secure location on your server if deploying. Restrict file permissions so only the application process can read it.
- **Key Rotation**: Periodically regenerate your API keys in the provider's dashboard and update your `.env` file. This is a good security practice.

### Step-by-Step Setup Guide

1.  **Download the Project**: Download the project folder to your computer. Let's say you put it on your desktop in a folder named `project1_AI_customer_inbox_agent`.

2.  **Open a Terminal/Command Prompt**: This is a text-based way to give commands to your computer.
    - **Windows**: Press `Windows Key + R`, type `cmd`, and press Enter.
    - **MacOS/Linux**: Search for "Terminal" in your applications.

3.  **Navigate to the Project Folder**: Use the `cd` command in the terminal to go into the project folder. For example:
    ```bash
    cd C:\Users\YourName\Desktop\project1_AI_customer_inbox_agent
    ```
    *(Replace `YourName` with your actual username)*

4.  **Create a Virtual Environment (Important!)**: This keeps the project's dependencies separate from other Python projects on your computer.
    ```bash
    python -m venv venv
    ```

5.  **Activate the Virtual Environment**:
    - **Windows (Command Prompt)**:
        ```cmd
        venv\Scripts\activate
        ```
    - **Windows (PowerShell)**:
        ```powershell
        venv\Scripts\Activate.ps1
        ```
        *(You might need to run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` first if you get an error)*
    - **MacOS/Linux**:
        ```bash
        source venv/bin/activate
        ```
    You should now see `(venv)` at the beginning of your command prompt.

6.  **Install Required Libraries**: Run this command to install all the Python libraries the project needs.
    ```bash
    pip install -r requirements.txt
    ```

7.  **Configure Your Settings (.env file)**:
    - Find the file named `.env.example` in the project folder.
    - Make a copy of it and rename the copy to `.env`.
    - Open the `.env` file in a text editor (like Notepad on Windows).
    - **Set your AI Provider**: Decide which AI provider you want to use (OpenAI, Anthropic, or Google). Change the line `LLM_PROVIDER=openai` to your choice (e.g., `LLM_PROVIDER=gemini`).
    - **Add your API Key**: Paste your API key into the correct line. If you chose Google, find the line `GEMINI_API_KEY=` and paste your key after the `=` sign. It should look like `GEMINI_API_KEY=your_actual_key_here`. Save and close the file.

8.  **Run the Application**: Now, run the application with this command:
    ```bash
    uvicorn app.main:app --reload
    ```

9.  **Open Your Browser**: Go to `http://127.0.0.1:8000` in your web browser. You should see the chat interface!

### Testing the Chat

- Type a question in the chat window (e.g., "Are you open on Sunday?").
- The AI should respond based on the information in the `data/knowledge_base` folder.
- Try asking something that sounds like a sales inquiry (e.g., "I need CCTV installed in Rongai. How much?"). Check the terminal where you ran `uvicorn` - it might log a "NEW LEAD" message.

## Using Different Communication Channels

### Website Chat (Default)
The demo UI at `http://127.0.0.1:8000` simulates a chat widget on your website. The `/chat` endpoint handles these messages.

### WhatsApp (Advanced Setup)
Connecting this AI to WhatsApp requires setting up the **WhatsApp Business Cloud API** with Meta. This involves creating an account on Meta for Developers, getting credentials (Access Token, Verify Token, Phone Number ID), and configuring webhooks. This is more complex and requires hosting your application online so Meta can send messages to it. The project code is prepared for this, but the setup is outside the scope of this basic guide.

### Email (Advanced Setup)
Similar to WhatsApp, connecting to email involves setting up rules or scripts to forward emails to the `/webhook/email` endpoint of this application. This also requires external setup.

## How to Customize for Your Business

This project is designed to be flexible. Here's how you can adapt it for your specific needs:

### 1. Update Your Business Information

- **Business Profile**: Edit the file `data/business_profile.json`. Change the `name`, `hours`, `location`, `services`, `contact info`, etc., to match your business details.
- **Knowledge Base**: Add or edit files in the `data/knowledge_base/` directory.
    - Create new `.md` (Markdown) files for different topics (e.g., `delivery_info.md`, `payment_methods.md`).
    - Write information in a question-and-answer format within these files (e.g., use `##` headings for topics like `## Pricing`).
    - The AI will use this information to answer customer questions. The more detailed and clear your files are, the better the AI will perform.

### 2. Change the AI Provider

- You can easily switch between OpenAI, Anthropic, and Google by changing the `LLM_PROVIDER` value in your `.env` file and adding the corresponding API key.

### 3. Modify the AI's Behavior

- **Agent Logic**: Look at `app/agent.py`. This file controls the main flow: intent detection, knowledge retrieval, response generation, and lead capture. You can modify the prompts or the logic here if you have some programming knowledge.
- **Prompts**: The `SYSTEM_PROMPT_TEMPLATE` in `agent.py` defines how the AI should behave (be friendly, concise, etc.). You can tweak this text.
- **Classification Tool**: The `CLASSIFY_TOOL` in `agent.py` defines how the AI categorizes messages (e.g., `faq`, `quote_request`, `greeting`). You can adjust the categories if needed.

### 4. Capture Different Types of Leads

- The lead capturing logic is in `app/agent.py` within the `handle_message` function. Currently, it captures a lead if `classification.get("is_lead")` is true. You can modify the criteria for what constitutes a lead.
- The `Lead` model in `app/models.py` defines what information is stored about a lead (customer ID, interest, urgency, etc.). You can add more fields if needed.

### 5. Integrate with Your CRM/Sales Notifications

- **Notifications**: The `app/notify.py` file handles what happens when a lead is captured. By default, it logs to `notifications.log`. You can modify this function to send an email, a Slack message, or make an API call to your CRM system (like Salesforce or HubSpot) to create a new lead record there.
- **Database**: The application uses SQLite by default (stored as `inbox_agent.db`). If you want to use a more robust database like PostgreSQL for production, you can change the `DATABASE_URL` in your `.env` file (e.g., `DATABASE_URL=postgresql://username:password@localhost/dbname`).

### 6. Customize the Web Interface

- The chat interface is defined in `static/index.html`. You can modify the HTML, CSS, and JavaScript here to change the look and feel, colors, logo, welcome message, etc., to match your brand.

By following these steps, you can tailor the AI Customer Inbox Agent to fit your business perfectly!
```

#the end