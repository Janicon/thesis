# Base code:
#   https://github.com/twitterdev/Twitter-API-v2-sample-code/tree/main/Tweet-Lookup
import requests
import json
from dateutil import parser
from datetime import datetime as dt
import pytz
import time

# Manually-set variables
input_filename = "./Collected Tweet IDs/searched_tweets_may_16.txt"
output_filename = "./Raw Data/05-16/raw_data_05-16" # DO NOT INCLUDE EXTENSION
override_batch = 0 # Starting batch if previous run reached limit (default: 0)

# To set your enviornment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
bearer_token = ""

# Get tweet IDs from file
def load_ids():
    my_file = open(input_filename, "r")

    # reading the file
    data = my_file.read()
    
    # replacing end splitting the text 
    # when newline ('\n') is seen.
    ids = data.split("\n")
    my_file.close()
    if ids[-1] == '':
        del ids[-1]

    # Merge list into comma separated query, by 100s
    id_strings = []
    start = 0
    end = len(ids)
    while(start + 100 < end):
        subset = ids[start:start + 100]

        id_string = subset[0]
        for i in range(1, len(subset)):
            id_string = id_string + "," + subset[i]

        id_strings.append(id_string)
        start += 100
    
    # Same as while loop, for <100 IDs
    subset = ids[start:end]
    id_string = subset[0]
    for i in range(1, len(subset)):
        id_string = id_string + "," + subset[i]
    id_strings.append(id_string)

    return id_strings

def create_url(IDs):
    tweet_fields = "tweet.fields=lang,author_id,created_at"
    # Tweet fields are adjustable.
    # Options include:
    # attachments, author_id, context_annotations,
    # conversation_id, created_at, entities, geo, id,
    # in_reply_to_user_id, lang, non_public_metrics, organic_metrics,
    # possibly_sensitive, promoted_metrics, public_metrics, referenced_tweets,
    # source, text, and withheld
    ids = "ids=" + IDs
    # You can adjust ids to include a single Tweets.
    # Or you can add to up to 100 comma-separated IDs
    url = "https://api.twitter.com/2/tweets?{}&{}".format(ids, tweet_fields)
    return url

def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2TweetLookupPython"
    return r

def connect_to_endpoint(url):
    global query_count
    response = requests.request("GET", url, auth=bearer_oauth)
    responses.append(response.status_code)
    print("Query ", query_count, " request response: ", response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Query ", query_count, " request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    query_count += 1
    return response.json()

# Initial ISO 8601 date time format
# https://stackoverflow.com/questions/79797/how-to-convert-local-time-string-to-utc
def convert_time(json):
    for cur in json:
        dt = cur['created_at']

        initial_dt = parser.parse(dt)

        local_tz = pytz.timezone("Asia/Manila")
        utc_dt = initial_dt.astimezone(local_tz)
        cur['created_at'] = utc_dt
    
    return json    
    
if __name__ == "__main__":
    if (bearer_token == ""):
        raise Exception("No token set")

    query_ids = load_ids()
    
    # Set defaults and overrides
    batchnum = override_batch
    query_count = override_batch * 10
    query_ids = query_ids[override_batch:]
    responses = []
    queries_done = 0

    # Fetch tweets in batches of 1000
    # Per batch, there are 10 sets of query ids (100 tweets per query), giving 1000 tweets per batch
    while batchnum * 10 < len(query_ids):
        json_obj = []
        try:            
            for query in query_ids[batchnum * 10:(batchnum + 1) * 10]:
                url = create_url(query)
                json_response = connect_to_endpoint(url)

                obj = json_response['data']
                obj = convert_time(obj)

                json_obj += obj

                queries_done += 1
                if queries_done % 300 == 0:
                    print("300 queries requested; standing by for API refresh.")
                    print("\tTime left: 15 minutes")
                    time.sleep(300)
                    print("\tTime left: 10 minutes")
                    time.sleep(300)
                    print("\tTime left: 5 minutes")
                    time.sleep(120)
                    print("\tTime left: 3 minutes")
                    time.sleep(120)
                    print("\tTime left: 1 minute")
                    time.sleep(60)

        except:
            # Write error log if query fails
            errtime = dt.now()
            with open("./Logs/" + errtime.strftime("DC %y-%m-%d %H.%M.%S.txt"), "w") as outfile:
                outfile.write(f"Data collection for file [{input_filename}]\n")
                outfile.write(errtime.strftime("%Y %B %d, %H:%M:%S"))
                outfile.write(f"\nQueries started at batch {override_batch}")
                outfile.write(f"\nQueries stopped at batch {batchnum} (Query {query_count % 10})")
                outfile.write("\nResponse codes:")
                outfile.write("\n\tQuery number\t|\tResponse")
                for i, res in enumerate(responses, start=override_batch * 10):
                    outfile.write(f"\n\t    {i}\t\t\t  {res}")
                break
        finally:
            if json_obj:
                # Save tweets to file
                json_str = json.dumps(json_obj, indent=4, sort_keys=True, default=str)
                
                with open(f"{output_filename}_{batchnum}.json", "w") as outfile:
                    outfile.write(json_str)
        
        batchnum += 1
    
    finishtime = dt.now()
    finishtime = finishtime.strftime("%Y %B %d, %H:%M:%S")
    print(f"Finished {finishtime}")