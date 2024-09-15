import random
from typing import List, Tuple
import streamlit as st

# Constants
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIMES = ["9:00-9:50", "10:00-10:50", "11:00-11:50", "12:00-12:50", "1:40-2:30", "2:40-3:30", "3:40-4:30"]
SECTIONS = ["A", "B", "C", "D", "E", "F"]
SUBJECTS = ["Software Engineering", "Software Engineering Lab", "Opensource", "Opensource Lab", "Operating System", "English", "Second Language"]
SUBJECT_HOURS = {
    "Software Engineering": 3,
    "Software Engineering Lab": 2,
    "Opensource": 3,
    "Opensource Lab": 2,
    "Operating System": 3,
    "English": 3,
    "Second Language": 3
}
TEACHERS = {
    "Software Engineering": ["Kanagaraj", "Balamurugan", "Vishnu Priya", "Sherin", "Prakash", "Stephen", "Gopinath"],
    "Software Engineering Lab": ["Kanagaraj", "Balamurugan", "Vishnu Priya", "Sherin", "Prakash", "Stephen", "Gopinath"],
    "Opensource": ["Margaret", "Sherin", "Vishnu Priya", "Mohana Priya", "Bhoomika", "Kavya"],
    "Opensource Lab": ["Margaret", "Sherin", "Vishnu Priya", "Mohana Priya", "Bhoomika", "Kavya"],
    "Operating System": ["Mohana Priya", "Stephen", "Gopinath", "Pratap", "Sudarshan", "Kanagaraj"],
    "English": ["Irona", "Preethi", "Geetha", "Arun", "Abhinav", "Gururaj"],
    "Second Language": ["Premkumar", "Ruth", "Ravishankar", "Neha Singh", "Vanshitha", "Siya"]
}
ROOMS = {
    "A": "M201",
    "B": "M202",
    "C": "M203",
    "D": "M204",
    "E": "M205",
    "F": "M206"
}
LAB_ROOMS = ["AL1", "AL2", "M1", "M2"]

# Parameters
POPULATION_SIZE = 10
GENERATIONS = 100
MUTATION_RATE = 0.01

# Genome representation: List of tuples (day, time, section, subject, teacher, room)
Genome = List[Tuple[str, str, str, str, str, str]]

def generate_genome() -> Genome:
    genome = []
    subject_hours_remaining = {section: SUBJECT_HOURS.copy() for section in SECTIONS}
    teacher_assignment = {section: {} for section in SECTIONS}  # Track which teacher is assigned to which subject for each section
    
    for section in SECTIONS:
        labs_scheduled = set()  # Track which labs have been scheduled
        for day in DAYS:
            day_subjects = set()
            for time in TIMES:
                if not any(subject_hours_remaining[section].values()):
                    genome.append((day, time, section, "Free", "N/A", ROOMS[section]))
                    continue
                
                # Select a subject that has remaining hours and isn't already chosen today
                available_subjects = [subject for subject, hours in subject_hours_remaining[section].items() if hours > 0 and subject not in day_subjects]
                
                if not available_subjects:
                    genome.append((day, time, section, "Free", "N/A", ROOMS[section]))
                    continue
                
                subject = random.choice(available_subjects)
                
                # Handle consistent teacher assignment
                if subject in teacher_assignment[section]:
                    teacher = teacher_assignment[section][subject]
                else:
                    # Assign a new teacher and ensure lab consistency
                    if subject.endswith("Lab"):
                        base_subject = subject.replace(" Lab", "")
                        if base_subject in teacher_assignment[section]:
                            teacher = teacher_assignment[section][base_subject]
                        else:
                            teacher = random.choice(TEACHERS[subject])
                            teacher_assignment[section][subject] = teacher
                            teacher_assignment[section][base_subject] = teacher
                    else:
                        teacher = random.choice(TEACHERS[subject])
                        teacher_assignment[section][subject] = teacher
                
                # Handle lab scheduling
                if subject.endswith("Lab"):
                    if subject not in labs_scheduled and subject_hours_remaining[section][subject] == 2 and time not in TIMES[-1:]:
                        lab_room = random.choice(LAB_ROOMS)
                        genome.append((day, time, section, subject, teacher, lab_room))
                        genome.append((day, TIMES[TIMES.index(time) + 1], section, subject, teacher, lab_room))
                        subject_hours_remaining[section][subject] -= 2
                        labs_scheduled.add(subject)
                        break  # Skip the next time slot since it's already filled
                else:
                    genome.append((day, time, section, subject, teacher, ROOMS[section]))
                    subject_hours_remaining[section][subject] -= 1
                    day_subjects.add(subject)
    
    # Ensure no days are holidays
    for section in SECTIONS:
        section_timetable = [entry for entry in genome if entry[2] == section]
        for day in DAYS:
            daily_schedule = [entry for entry in section_timetable if entry[0] == day]
            if all(entry[3] == "Free" for entry in daily_schedule):
                available_subjects = [subject for subject, hours in subject_hours_remaining[section].items() if hours > 0]
                if available_subjects:
                    subject = random.choice(available_subjects)
                    teacher = teacher_assignment[section].get(subject, random.choice(TEACHERS[subject]))
                    time_slot = random.choice(TIMES)
                    genome.append((day, time_slot, section, subject, teacher, ROOMS[section]))
                    subject_hours_remaining[section][subject] -= 1
    
    return genome

def calculate_fitness(genome: Genome) -> int:
    fitness = 0
    for section in SECTIONS:
        section_timetable = [entry for entry in genome if entry[2] == section]
        
        # Constraint: no subject repeats more than once per day (except labs)
        for day in DAYS:
            daily_schedule = [entry for entry in section_timetable if entry[0] == day]
            subjects_today = [entry[3] for entry in daily_schedule if not entry[3].endswith("Lab")]
            if len(subjects_today) != len(set(subjects_today)):
                fitness -= 1
        
        # Constraint: fixed room per section
        for entry in section_timetable:
            if not entry[3].endswith("Lab") and entry[5] != ROOMS[section]:
                fitness -= 1
        
        # Constraint: labs should be continuous and in lab rooms
        for day in DAYS:
            daily_schedule = [entry for entry in section_timetable if entry[0] == day]
            for i in range(len(daily_schedule) - 1):
                if daily_schedule[i][3].endswith("Lab") and daily_schedule[i+1][3].endswith("Lab"):
                    if daily_schedule[i][3] == daily_schedule[i+1][3] and daily_schedule[i][5] == daily_schedule[i+1][5]:
                        continue
                    else:
                        fitness -= 1
        
        # Constraint: no holidays (every day must have at least one class)
        for day in DAYS:
            daily_schedule = [entry for entry in section_timetable if entry[0] == day]
            if all(entry[3] == "Free" for entry in daily_schedule):
                fitness -= 1

        # Constraint: Consistent teacher assignment for each subject
        teacher_assignments = {entry[3]: entry[4] for entry in section_timetable if entry[3] != "Free"}
        if len(teacher_assignments) != len(set(teacher_assignments.values())):
            fitness -= 1
        
        # Constraint: No subject should exceed its allocated hours
        subject_count = {subject: 0 for subject in SUBJECTS}
        for entry in section_timetable:
            if entry[3] != "Free":
                subject_count[entry[3]] += 1
        for subject, count in subject_count.items():
            if count > SUBJECT_HOURS[subject]:
                fitness -= 1
    
    return fitness

def select_parents(population: List[Genome]) -> Tuple[Genome, Genome]:
    return random.sample(population, 2)

def crossover(parent1: Genome, parent2: Genome) -> Tuple[Genome, Genome]:
    index = random.randint(0, len(parent1) - 1)
    child1 = parent1[:index] + parent2[index:]
    child2 = parent2[:index] + parent1[index:]
    return child1, child2

def mutate(genome: Genome) -> Genome:
    if random.random() < MUTATION_RATE:
        index = random.randint(0, len(genome) - 1)
        day, time, section, subject, teacher, room = genome[index]
        if subject != "Free":
            new_teacher = random.choice(TEACHERS[subject])
            genome[index] = (day, time, section, subject, new_teacher, room)
    return genome

def genetic_algorithm() -> Genome:
    population = [generate_genome() for _ in range(POPULATION_SIZE)]
    
    for _ in range(GENERATIONS):
        population = sorted(population, key=calculate_fitness, reverse=True)
        
        next_generation = population[:2]  # Elitism: carry the best solutions to the next generation
        
        while len(next_generation) < POPULATION_SIZE:
            parent1, parent2 = select_parents(population)
            child1, child2 = crossover(parent1, parent2)
            next_generation.append(mutate(child1))
            next_generation.append(mutate(child2))
        
        population = next_generation
    
    # Best solution
    best_genome = max(population, key=calculate_fitness)
    return best_genome

def format_timetable(genome: Genome, section: str) -> str:
    timetable = f"Timetable for Section {section}\n"
    section_genome = [entry for entry in genome if entry[2] == section]
    
    for day in DAYS:
        timetable += f"{day}\n"
        day_genome = [entry for entry in section_genome if entry[0] == day]
        for time in TIMES:
            entry = next((entry for entry in day_genome if entry[1] == time), None)
            if entry:
                timetable += f"{time}: {entry[3]} | {entry[4]} | {entry[5]}\n"
            else:
                timetable += f"{time}: Free\n"
        timetable += "\n"
    
    return timetable

# Streamlit UI
st.title("College Timetable Generator")

section = st.selectbox("Select Section", SECTIONS)
if st.button("Generate Timetable"):
    genome = genetic_algorithm()
    timetable = format_timetable(genome, section)
    st.text(timetable)