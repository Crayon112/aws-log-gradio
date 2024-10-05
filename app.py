import time
import boto3
import gradio


logs = boto3.client("logs")


def list_all_log_groups():
    log_group_names = []

    paginator = logs.get_paginator('describe_log_groups')
    for page in paginator.paginate():
        for log_group in page['logGroups']:
            log_group_names.append(log_group['logGroupName'])

    return log_group_names


def n_days_ago(now: int = int(time.time()), n: int = 0):
    return int(now) - 24 * 60 * 60 * 1000 * n


def ravel(something):
    if not isinstance(something, list):
        return [something]

    results = []
    for s in something:
        results.extend(ravel(s))
    return results


def logs_from_query(
    log_group_name: str,
    query: str,
    start_timestamp: int = n_days_ago(n = 1),
    end_timestamp: int = n_days_ago(),
):
    response = logs.start_query(
        logGroupName=log_group_name,
        startTime=start_timestamp,
        endTime=end_timestamp,
        queryString=query,
    )
    query_id = response.get("queryId", 0)

    response = None
    while response is None or response.get("status", "Running") != "Complete":
        response = logs.get_query_results(queryId=query_id)
        time.sleep(0.5)

    records = response.get("results", [])
    messages = []
    records = ravel(records)
    for record in records:
        if record.get("field") != "@message":
            continue
        messages.append(record.get("value", ""))

    return messages


def search(
    query, log_group_names,
    start_timestamp=n_days_ago(n = 1),
    end_timestamp=n_days_ago(),
):
    results = []
    for log_group_name in log_group_names:
        this_result = logs_from_query(
            log_group_name=log_group_name,
            query=query,
            start_timestamp=int(start_timestamp),
            end_timestamp=int(end_timestamp),
        )
        for r in this_result:
            results.append([log_group_name, r])

    return results


log_groups = list_all_log_groups()


with gradio.Blocks() as demo:
    with gradio.Row():
        with gradio.Column(scale=4):
            query_text_box = gradio.Textbox(label="搜索项")
            with gradio.Row():
                start_timestamp = gradio.DateTime(label="起始时间")
                end_timestamp = gradio.DateTime(label="结束时间")
            dropdown = gradio.Dropdown(log_groups, label="日志组", multiselect=True)
            search_button = gradio.Button("搜索")
        with gradio.Column(scale=6):
            show_area = gradio.List(headers=["日志组", "日志消息"], col_count=2)

    search_button.click(
        search,
        inputs=[query_text_box, dropdown, start_timestamp, end_timestamp],
        outputs=show_area,
    )


if __name__ == '__main__':
    demo.launch()

