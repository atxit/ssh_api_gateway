

concurrent_sessions = list(range(0, 5))
completed_sessions = concurrent_sessions.copy()




def start_test_job():
    start_time = int(time.time())
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(concurrent_sessions)) as executor:
        future_ssh = {executor.submit(ssh_post, job, session_id): session_id for session_id in concurrent_sessions}
        for future_id in concurrent.futures.as_completed(future_ssh):
            session_id = future_id.result()
            print(f'session {session_id} completed')
            try:
                compeleted_sessions.remove(session_id)
            except Exception:
                print('duplicate session ID...')
            print(f'timer is {int(time.time() - start_time)} seconds')
    if len(compeleted_sessions) > 0:
        print('hmmm, we have missing data')
    else:
        print(f'all sessions accounted for')
    print(f'job/s took {int(time.time() - start_time)} seconds to complete')
