# Digantara-Backend-Assessment-Kiran-
Step-by-Step Guide: Running the Scheduler Microservice
This guide will walk you through every step required to set up your environment, run the Python code, and interact with the running application.

Step 1: Create a Project Folder
First, let's create a dedicated folder (also known as a directory) for our project. This keeps all our files organized.

Open your terminal or command prompt.

Navigate to a place where you want to store your project (like your Desktop or Documents folder).

Create a new directory and move into it. You can name it whatever you like; we'll use scheduler_project.

# Create the directory
mkdir scheduler_project

# Move into the newly created directory
cd scheduler_project

You are now inside your project folder. All subsequent commands should be run from here.

Step 2: Create the Python File
Now, you need to create the Python file that will contain the microservice code.

Create a new file named scheduler_microservice.py inside the scheduler_project folder. You can do this with a text editor like VS Code, Sublime Text, Notepad, or by using a terminal command:

On macOS or Linux: touch scheduler_microservice.py

On Windows: echo. > scheduler_microservice.py

Copy the code from the immersive document on the right-hand side of your screen.

Paste the entire code into the scheduler_microservice.py file you just created and save it.

Step 3: Set Up a Virtual Environment (Highly Recommended)
A virtual environment is a self-contained directory that holds a specific version of Python plus all the necessary packages for a project. This is a crucial best practice as it prevents conflicts between different projects' dependencies.

From your terminal (while inside the scheduler_project folder), create a virtual environment. We'll name it venv.

python -m venv venv

Now, activate the virtual environment. The command differs based on your operating system:

On macOS and Linux:

source venv/bin/activate

On Windows (Command Prompt):

venv\Scripts\activate

Once activated, you will see (venv) at the beginning of your terminal prompt. This indicates that any packages you install will be isolated to this environment.

Step 4: Install the Required Libraries
With the virtual environment active, we can now install the Python libraries the project depends on.

Run the following pip command in your terminal. This reads the list of required packages and installs them.

pip install "fastapi[all]" sqlmodel apscheduler

Pip will download and install fastapi, uvicorn (the server), sqlmodel, apscheduler, and their dependencies. Wait for the process to complete.

Step 5: Run the Microservice
Everything is now in place. Let's start the server!

In your terminal (making sure you are in the scheduler_project directory and your virtual environment is active), run the following command:

uvicorn scheduler_microservice:app --reload
#########

If everything is successful, you will see output in your terminal that looks something like this:

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using statreload
INFO:     Application startup...
INFO:     Creating database and tables...
INFO:     ... (database logs) ...
INFO:     Database and tables created successfully.
INFO:     Loading and scheduling all jobs from the database...
INFO:     All jobs loaded.
INFO:     Started server process [54321]
INFO:     Waiting for application startup.
INFO:     Application startup complete.

Your scheduler microservice is now live and running on your local machine!

Step 6: Interact With Your Live API
The most powerful feature of FastAPI is its automatic interactive documentation.

Open your web browser (like Chrome, Firefox, or Safari).

Navigate to the following URL: http://127.0.0.1:8000/docs

You will be greeted by the Swagger UI interface. This is a complete, interactive dashboard for your API. You can see all the available endpoints (/jobs, /jobs/{id}, etc.) and test them directly from your browser.

Let's create a job:

Click on the POST /jobs endpoint to expand it.

Click the "Try it out" button on the right side.

This will make the "Request body" field editable. Replace the existing content with the following JSON to create a job that runs every minute:

{
  "name": "My First Scheduled Job",
  "job_type": "email_notification",
  "cron_string": "* * * * *",
  "job_params": {
    "to": "user@example.com",
    "subject": "Minute-by-Minute Update",
    "body": "This is a test email sent from the scheduler."
  }
}

Click the blue "Execute" button.

Check the results:

In your browser: You should see a "201 Created" response with the details of the job you just created.

In your terminal: Go back to the terminal where uvicorn is running. You will see the log output from the job being executed every minute!

INFO:     Executing job 1: 'My First Scheduled Job'
INFO:     --- JOB EXECUTING: Sending Email ---
INFO:     To: user@example.com
INFO:     Subject: Minute-by-Minute Update
INFO:     Body: This is a test email sent from the scheduler.
INFO:     --- JOB COMPLETE ---
INFO:     Successfully executed and updated job 1.

List all jobs:

In the browser documentation, expand the GET /jobs endpoint.

Click "Try it out" and then "Execute".

You will see a list containing the job you just created.

Step 7: Stopping the Application
When you are finished, you can stop the server.

Go back to your terminal window where the server is running.

Press Ctrl + C on your keyboard. The server will shut down gracefully.

To deactivate the virtual environment, simply type:

deactivate

You have now successfully set up, run, tested, and shut down the scheduler microservice.
