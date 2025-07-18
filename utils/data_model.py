from datetime import date, datetime
from typing import List, Dict

class Task:
    def __init__(self, name, util, frequency_days, last_execution):
        self.name = name
        self.util = util
        self.freq = frequency_days
        self.new_util = 0
        self.util_ratio = round(util / frequency_days, 2)
        self.final_util_ratio = 0
        self.is_last_execution = last_execution

    def update_new_util(self, new_value):
        self.new_util = round(new_value, 2)

    def update_final_util_ratio(self, new_value):
        self.final_util_ratio = round(new_value, 2)

    def to_dict(self):
        return {
            "name": self.name,
            "util": self.util,
            "freq": self.freq,
            "new_util": self.new_util,
            "util_ratio": self.util_ratio,
            "final_util_ratio": self.final_util_ratio,
            "is_last_execution": self.is_last_execution
        }

    @classmethod
    def from_dict(cls, data):
        task = cls(
            name=data["name"],
            util=data["util"],
            frequency_days=data["freq"],
            last_execution=data["is_last_execution"]
        )
        task.update_new_util(data.get("new_util", 0))
        task.update_final_util_ratio(data.get("final_util_ratio", 0))
        return task

class WorkPackage:
    def __init__(self, name, duration, due_date, date_mapping):
        self.name = name
        self.dur = duration
        self.due = due_date if isinstance(due_date, date) else datetime.fromisoformat(due_date).date()
        self.due_map = date_mapping[self.due]
        self.tasks: List[Task] = []
        self.dependencies: List[tuple] = []  # list of (WorkPackage, List[Task])
        self.new_start = -1
        self.following_wps: List[WorkPackage] = []

    def add_task(self, task: Task):
        self.tasks.append(task)

    def get_task_names(self):
        return set(task.name for task in self.tasks)
    
    def update_new_start(self, new_value):
        self.new_start = new_value

    def to_dict(self):
        return {
            "name": self.name,
            "duration": self.dur,
            "due_date": self.due.isoformat(),
            "due_map": self.due_map,
            "new_start": self.new_start,
            "tasks": [t.to_dict() for t in self.tasks],
            "dependencies": [
                (wp.name, [t.name for t in tasks]) for wp, tasks in self.dependencies
            ],
            "following_wps": [wp.name for wp in self.following_wps]
        }

    @classmethod
    def from_dict(cls, data, date_mapping=None):
        wp = cls(
            name=data["name"],
            duration=data["duration"],
            due_date=data["due_date"],
            date_mapping = date_mapping,
        )
        wp.new_start = data.get("new_start", -1)
        wp.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        # not resolving dependencies/following_wps until Aircraft.from_dict
        wp._dependencies_serialized = data.get("dependencies", [])
        wp._following_wps_names = data.get("following_wps", [])
        return wp
    
class Aircraft:
    def __init__(self, aircraft_id):
        self.ac = aircraft_id
        self.wps: List[WorkPackage] = []

    def add_workpackage(self, wp: WorkPackage):
        if wp.name not in self.wps:
            self.wps.append(wp)

    # dependencies between the wps of an aircraft (shared tasks)
    def find_all_dependencies(self): 
        sorted_wps = sorted(self.wps, key=lambda wp: wp.due_map, reverse=True) 

        for i, wp1 in enumerate(sorted_wps):  # get the wp of greatest due date first
            wp1_tasks = wp1.get_task_names()  
            wp1_task_map = {task.name: task for task in wp1.tasks} 

            for wp2 in sorted_wps[i+1:]:  # earlier in time
                wp2_tasks = wp2.get_task_names()  
                wp2_task_map = {task.name: task for task in wp2.tasks}  
                
                shared_task_names = wp1_task_map.keys() & wp2_task_map.keys()
                # store the info of the common tasks in the second WP
                shared_tasks = [wp1_task_map[name] for name in shared_task_names] # tasks belong to the latest WP

                if not hasattr(wp2, 'dependencies'):
                    wp2.dependencies = []  
                if shared_tasks:
                    wp2.dependencies.append((wp1, shared_tasks)) # a previous WP depends on the latest WP
                    break # found closest wp, no need to search further
        
        
    def find_following_wps(self, wp:WorkPackage): 
        sorted_wps = sorted(self.wps, key=lambda wp: wp.due_map, reverse=True) 

        for i, wp1 in enumerate(sorted_wps):  # get the wp of greatest due date first, stop when you reach the one under examination
            if wp.name == wp1.name:
                break
            else:
                wp.following_wps.append(wp1)  


    def find_between_wps(self, wp1: WorkPackage, wp2: WorkPackage):

        lower_due_map = min(wp1.due_map, wp2.due_map)
        upper_due_map = max(wp1.due_map, wp2.due_map)

        wps_btw = [wp for wp in self.wps if lower_due_map < wp.due_map < upper_due_map and wp != wp1 and wp != wp2]

        return wps_btw

    def to_dict(self):
        return {
            "aircraft_id": self.ac,
            "wps": [wp.to_dict() for wp in self.wps]
        }

    @classmethod
    def from_dict(cls, data, date_mapping=None):
        ac = cls(data["aircraft_id"])
        name_to_wp: Dict[str, WorkPackage] = {}

        for wp_data in data.get("wps", []):
            wp = WorkPackage.from_dict(wp_data, date_mapping=date_mapping)
            ac.add_workpackage(wp)
            name_to_wp[wp.name] = wp

        for wp in ac.wps:
            wp.dependencies = []
            for dep_name, task_names in getattr(wp, "_dependencies_serialized", []):
                if dep_name in name_to_wp:
                    dep_wp = name_to_wp[dep_name]
                    task_map = {t.name: t for t in dep_wp.tasks}
                    tasks = [task_map[name] for name in task_names if name in task_map]
                    wp.dependencies.append((dep_wp, tasks))

            wp.following_wps = [
                name_to_wp[name] for name in getattr(wp, "_following_wps_names", []) if name in name_to_wp
            ]

        return ac
