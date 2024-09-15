import random
from typing import List, Tuple
import streamlit as st
from ortools.sat.python import cp_model

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

def create_initial_solution() -> Genome:
    model = cp_model.CpModel()
    
    # Variables
    timetable = {}
    for section in SECTIONS:
        for day in DAYS:
            for time in TIMES:
                for subject in SUBJECTS:
                    timetable[(section, day, time, subject)] = model.NewBoolVar(f'{section}{day}{time}_{subject}')
    
    # Constraints
    for section in SECTIONS:
        for day in DAYS:
            for time in TIMES:
                model.Add(sum(timetable[(section, day, time, subject)] for subject in SUBJECTS) <= 1)
    
    for section in SECTIONS:
        for day in DAYS:
            for subject in SUBJECTS:
                num_hours = SUBJECT_HOURS[subject]
                if num_hours > 0:
                    model.Add(sum(timetable[(section, day, time, subject)] for time in TIMES) == num_hours)
    
    # Create solver and solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status != cp_model.OPTIMAL:
        raise ValueError("No feasible solution found with constraints.")
    
    genome = []
    for (section, day, time, subject) in timetable:
        if solver.Value(timetable[(section, day, time, subject)]):
            teacher = random.choice(TEACHERS[subject])
            room = random.choice(LAB_ROOMS) if "Lab" in subject else ROOMS[section]
            genome.append((day, time, section, subject, teacher, room))
    
    return genome

def calculate_fitness(genome: Genome) -> int:
    fitness = 0
    teacher_assignment = {}
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
        for entry in section_timetable:
            day, time, section, subject, teacher, room = entry
            if subject != "Free":
                if subject in teacher_assignment:
                    if teacher_assignment[subject] != teacher:
                        fitness -= 1
                else:
                    teacher_assignment[subject] = teacher
    
    return fitness

def select_parents(population: List[Genome]) -> Tuple[Genome, Genome]:
    return random.sample(population, 2)

def crossover(parent1: Genome, parent2: Genome) -> Tuple[Genome, Genome]:
    # One-point crossover
    point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2

def mutate(genome: Genome) -> Genome:
    for i in range(len(genome)):
        if random.random() < MUTATION_RATE:
            day, time, section, subject, teacher, room = genome[i]
            if subject != "Free":
                # Reassign teacher for the subject
                teacher = random.choice(TEACHERS[subject])
            genome[i] = (day, time, section, subject, teacher, room)
    return genome

def genetic_algorithm() -> Genome:
    # Initial population
    population = [create_initial_solution() for _ in range(POPULATION_SIZE)]
    
    for generation in range(GENERATIONS):
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
                timetable += f"{time}: {entry[3]} with {entry[4]} in {entry[5]}\n"
            else:
                timetable += f"{time}: Free\n"
        timetable += "\n"
    
    return timetable

def main():
    st.title("Automatic Timetable Generator")
    
    # Generate timetable
    best_genome = genetic_algorithm()
    
    # Display timetables for all sections
    for section in SECTIONS:
        timetable = format_timetable(best_genome, section)
        st.text(timetable)

if __name__ == "__main__":
    main()
