import json
import os
import tempfile
from fastapi import FastAPI
from langchain.agents.agent_toolkits import GmailToolkit
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_community.tools.gmail import get_gmail_credentials
from langchain_community.tools.gmail.utils import build_resource_service


# * FastAPI Application Documentation**

#
# This FastAPI application is a comprehensive tool designed to aid real estate agents in streamlining their workflow. The application integrates advanced features like AI-driven email assistance, client management, and market analysis tools.
#
# **Running the FastAPI Application:**
#
# To start the application, you need to have FastAPI and Uvicorn installed. Uvicorn is an ASGI server implementation, which serves as the gateway to making your FastAPI application available for web requests.
#
# 1. **Install FastAPI and Uvicorn (if not already installed):**
#    ```bash
#    pip install fastapi uvicorn
#    ```
#
# 2. **Run the Application:**
#    Navigate to the directory where your FastAPI application file (e.g., `main.py`) is located, and run the following command in your terminal:
#    ```bash
#    uvicorn main:AIemail --reload
#    ```
#    - `main`: The file name of your FastAPI application (without the `.py` extension).
#    - `AIemail`: The instance of the FastAPI application in your `main.py` file.
#    - `--reload`: Enables auto-reload so the server will restart upon code changes. This is useful for development but should be omitted in a production environment.
#
# 3. **Accessing the API:**
#    Once running, you can access the API at `http://127.0.0.1:8000`. The API provides various endpoints, including:
#    - `/`: A simple greeting endpoint.
#    - `/email-Query`: Endpoint to process email queries using AI and Gmail integration.
#    - `/Catch-Me-UP`: Endpoint to get a summary of recent emails.
# 

class user:
    name: str = ""
    key: str = ""
    query: str

    # going to use this string to write to a file so that the email query will work
    # at the end of a query we must clear both that file and this class
    credentials: str = ""
    token: str = ""


# FastAPI instance

AIemail = FastAPI()


@AIemail.get("/")
def say_hello():
    """
        A simple API endpoint to greet the user.

        This endpoint provides a basic greeting to the user by returning
        a JSON object with a fixed user greeting. It serves as a straightforward
        way to test the API's basic functionality and confirm service operability.

        No parameters are required to access this endpoint, making it an
        ideal initial test point for API interaction or to perform a simple health check.

        Returns:
            JSON: A fixed response with a greeting message.

        Example:
            Response format: {"User": "Res user 1"}

            A GET request to this endpoint yields a JSON response containing a greeting
            to 'Res user 1', demonstrating the API is responsive and functioning as expected.
        """
    return {"User": "Res user 1"}



@AIemail.post("/email-Query")
def perform_query(request: dict):
    """
        Processes an email query request, setting up user credentials and performing the query.

        This endpoint accepts a POST request with user credentials and query details. It updates
        the user's information, sets the OpenAI API key environment variable, establishes a Gmail
        connection, initializes an agent, and runs the provided query. The function is designed to handle
        email-related queries using the OpenAI and Google APIs.

        Parameters:
            request (dict): A dictionary containing user information and query details.
                            Expected keys include 'OpenAiKey', 'googleCreds', 'GoogleToken', 'name', and 'Query'.

        Operations:
            1. Sets user information based on the request.
            2. Establishes OpenAI API key environment variable.
            3. Builds a Gmail connection using user tokens and credentials.
            4. Initializes an agent with the provided tools and model.
            5. Performs the user's query with the initialized agent.

        Returns:
            JSON: The response from performing the email query with relevant details or results.

        Example:
            POST request body format:
            {
                "OpenAiKey": "<Your-OpenAi-Key>",
                "googleCreds": "<Your-Google-Credentials>",
                "GoogleToken": "<Your-Google-Token>",
                "name": "<User-Name>",
                "Query": "<Query-String>"
            }

            A POST request to this endpoint with the required keys in the request body will process the email query
            and return the results or details of the operation.
        """
    # add info to the users name
    user.key = request["OpenAiKey"]
    user.credentials = request["googleCreds"]
    user.token = request["GoogleToken"]
    user.name = request["name"]
    user.query = request["Query"]

    os.environ["OPENAI_API_KEY"] = user.key

    # uplaod credentials to file
    TK = buildGmailConnenction(user.token, user.credentials)

    llm = ChatOpenAI(model="gpt-4")
    agent = initialize_agent(
        tools=TK.get_tools(),
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    )

    # run query
    response = agent.run(user.query)

    user.name = user.credentials = user.key = user.query = ""

    user.name = user.credentials = user.key = user.query = "0000000000"

    return response


def email_query(q: str):
    # build agent
    llm = ChatOpenAI(model="gpt-4")  # Pass the API key from the environment variable
    toolkit = GmailToolkit()
    agent = initialize_agent(
        tools=toolkit.get_tools(),
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, handle_parsing_errors=True, verbose=True
    )

    # return agents answer
    return {"Query": agent.run(q)}


def buildGmailConnenction(token, creds):
    # Create a temporary file for the token

    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as token_temp:
        # Ensure token is a dictionary and then convert it to a JSON-formatted string
        token_json = json.dumps(token)
        token_temp.write(token_json)
        token_temp_path = token_temp.name  # Save the path for later use

    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as creds_temp:
        # Same for creds
        creds_json = json.dumps(creds)
        creds_temp.write(creds_json)
        creds_temp_path = creds_temp.name  # Save the path for later use

    # Use the paths of the temporary files in your function
    credentials = get_gmail_credentials(
        token_file=token_temp_path,
        scopes=["https://mail.google.com/"],
        client_secrets_file=creds_temp_path,
    )

    api_resource = build_resource_service(credentials=credentials)
    toolkit = GmailToolkit(api_resource=api_resource)

    # Cleanup: Delete the temporary files now that we're done
    os.remove(token_temp_path)
    os.remove(creds_temp_path)

    return toolkit


@AIemail.post("/Catch-Me-UP")
def catchMeUP(request: dict):
    """
        Retrieves a summary of the most recent emails related to specific work topics.

        This endpoint processes a request to catch up on recent emails, particularly focusing on work-related topics.
        It accepts user credentials and query parameters, establishes a Gmail connection, and utilizes an OpenAI
        agent to generate a summary of emails from the last two days, specifically targeting topics like crypto,
        real estate, and specific market reports. If no relevant emails are found, it indicates that no work-related
        emails were present.

        Parameters:
            request (dict): A dictionary containing user information and OpenAI key.
                            Expected keys are 'OpenAiKey', 'googleCreds', 'GoogleToken', and 'name'.

        Operations:
            1. Updates user information with the request details.
            2. Establishes OpenAI API key environment variable.
            3. Builds Gmail connection using user tokens and credentials.
            4. Initializes an OpenAI agent with the provided tools and model.
            5. Executes a predefined query to summarize the latest work-related emails.
            6. Clears sensitive user information after processing.

        Returns:
            JSON: A summary of relevant emails or a notification of no significant work-related emails.

        Example:
            POST request body format:
            {
                "OpenAiKey": "<Your-OpenAi-Key>",
                "googleCreds": "<Your-Google-Credentials>",
                "GoogleToken": "<Your-Google-Token>",
                "name": "<User-Name>"
            }

            After sending a POST request to this endpoint with the required keys, it processes the email summaries and returns
            either a summary of recent work-related emails or a message indicating no significant emails were found.
        """
    user.key = request["OpenAiKey"]
    user.credentials = request["googleCreds"]
    user.token = request["GoogleToken"]
    user.name = request["name"]

    # this is going to seach for any emails from clients/ inquiries
    # Im thinking here we can pass through some extra details like look at emails from a list of clients
    # Or we can store anothe element in our app where a user can define exactly what they want this update to be

    # this will tigger every time a user hits " catch me up" or we could just have it trigger every 24hrs and display it on the left side
    # we could pass the client data as a parameter for this one and just add that string variable to the query prompt below
    user.query = "Can you catch me up on my emails. I am a crypto investor so curate this update as so"
    os.environ["OPENAI_API_KEY"] = user.key

    # uplaod credentials to file
    TK = buildGmailConnenction(user.token, user.credentials)

    llm = ChatOpenAI(model="gpt-4-1106-preview")
    agent = initialize_agent(
        tools=TK.get_tools(),
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, handle_parsing_errors=True
    )

    # run query
    response = agent.run(user.query)

    user.name = user.credentials = user.key = user.query = ""

    user.name = user.credentials = user.key = user.query = "0000000000"

    return response
