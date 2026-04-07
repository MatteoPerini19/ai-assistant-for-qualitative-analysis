# Notes to myself about the project 



## Prompt for implementation 

If you find expressions such as "to discuss" or "we can consider if", choose a simple and reasonable implementation but CLEARLY MARK THEM as only TEMPORARY implementations. In the comments in the scripts, include red emojies "🔴" to attract attention on them. 

If there are complex features that are an addition to the core functining of the project (e.g., having a separate script for conducting a comparative analysis), don't include them in the first round of code writing. However, in your answer write a note stating precisely what features described in the blueprint are not implemented yet. 

## ???

Graded relative score: 
-3  strongly text 1
-2  moderately text 1
-1  slightly text 1
 0  tie
+1  slightly text 2
+2  moderately text 2
+3  strongly text 2



## OPTIONAL FEATURES TO REFLECT ABOUT 

-1-
In the prompt for the LLM, include, as context, all or part of all the other texts in the dataset. In this way, if the LLM has to give a score, it has valuable context to use to know how high or low a certain text might be considering the alternative texts. This parallels what a human rater does when reading multiple texts. 

Also we need the script to estimate if the context would become too big for the LLM (degrading performance), in which case we should opt for a random sample of N texts provided as context (based on the average length of prompts and the maximum allowed tokens). In the random selection, we can consider prioritizing texts that are similar (i.e., same participant_ID and same task_ID). 
If additional texts are included as context in the prompt for the LLM, remember to include the task description  related to the text, in case this changes between different prompts (to save tokens, it is better to provide the task description only once, and below that attach all the task-specific comparison texts).

-1.1-
Bradley–Terry/Thurstone-style comparative analysis 

-2-
Create X different ways in which we ask the LLM to conduct the task, and include all of them in different prompts. 
-> generalizability. 

-3-
Parallel calls, for efficiency. 

-3-
Audit / council approach
- **multi-model ensemble scoring**
- **auditor model that reviews another model's coding**


-4-
Logprobs / entropy measures
-> uncertainty diagnostics using token-level metrics



-5-
Specifically for my **study with 4 conditions** per participant, namely 2 treatment conditions (awe) and 2 control conditions (funny, neutral):
If we evaluate this with the comparative approach, we should compare each text in the treatment condition with both texts in the control conditions, so for each text in the control condition we get comparative judgments for both control texts. 


-5-
Data immutability: compute hashes for input CSV and any referenced text/audio files at runtime (or at least for the subset used).


-6-
Allow multiple types of analyses at the same time. 

E.g., data type. 
Currently, we write something like this in the config file: 
    "we should add a note here for the user, that in case they want the LLMs to use different types of data for the same analysis (e.g., one ordinal item and one categortical item), we recommend running the analysis multiple times with different configurations."  

### OTHER PLATFORMS 

-1-
🟢 Fastest path: **Gradio**. Gradio is built precisely for wrapping Python functions in a web UI very quickly. It has a high-level ChatInterface for chatbot-style UIs, a File component for uploads/downloads, and built-in sharing options so you can expose a prototype fast without making users install anything. For a research or prototype tool, this is often the sweet spot.  ￼

🔵 Better for dashboards and result inspection: **Streamlit**. Streamlit gives you chat elements, file uploaders, tables, widgets, and a more “data app” feel. If your output includes long CSVs, summarized wide outputs, diagnostics, sanity checks, and maybe preview tables or plots, Streamlit is often nicer than a chat-only front end.  ￼

🟣 Best long-term architecture: **FastAPI** backend plus a simple frontend. FastAPI is a production-grade Python API framework, supports file uploads, and has background-task support for jobs that should continue after the initial response. This is the more serious route if you think your prototype could become a real product, not just a demo.  ￼


### TO SEARCH 

-1-
Advanced prompt engineering features. Examples:
- Repetition 
- Keep the core information at the end 
- Context lenght 
- ... 



### FEATURES WE CAN TEST IN A METHODOLOGICAL PAPER 

**Method for testing:**

Look for papers that (1) have been published in the best psychology journals, (2) contain qualitative analyses with a similar approach done by human raters (using them as ground truth), (3) and have open data. 
Then look for the approach that best approximates that, computing inter-rater reliability with human raters. 
Then, estimate the statistical significance / credible intervals of these results, to know if the LLM approach IRR with humans differ statistically (1) with the human raters themselves and (2) between different approaches. 

A simpler method: 
Just test if there is a significant difference between the AI outputs given different features, then, if a difference is significant, choose the one that, by logic, has the highest reliability (e.g., mean of 100 calls vs. 1 single call).

**Features to test:**

1. 100 calls vs. 1 call 
2. Temperature 
3. Providing massive context from all the other texts in the dataset 
4. ...


## Generalizing features 

This sectopm contains a (likely incomplete) description of the features that should the project that, for how I'm writing it, are specific for my studies and that, for making the software public, should be generalized. 


### Name of the variables and files 

Depending on how we let the user interact with the software, we should find a smooth way to make this software compatible with the user's dataset and files. 

E.g.:
- Name of the dataset 
- Name of the variables 
- Name of the audio or text files 
- Folders 

For features we should allow multiple options:
- The texts are within the main csv file or as separate files 
- ...


