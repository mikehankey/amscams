from lib.PipeUtil import load_json_file

unsolved_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_UNSOLVED.json"
solved_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_SOLVED.json"
failed_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_FAILED.json"

unsolved = load_json_file(unsolved_file)
solved = load_json_file(solved_file)
failed = load_json_file(failed_file)

print("UN:", len(unsolved))
print("SLV:", len(solved))
print("FLD:", len(failed))

#for ev in unsolved:
#   print(ev['id'])
