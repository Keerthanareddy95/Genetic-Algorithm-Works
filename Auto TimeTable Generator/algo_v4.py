import random
from typing import List, Tuple
import pandas as pd
import streamlit as st

# Load CSV data
rooms_df = pd.read_csv('Data/rooms.csv')
subjects_df = pd.read_csv('Data/subjects.csv')
sections_df = pd.read_csv('Data/sections.csv')

# Constants
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIMES = ["9:00-9:50", "10:00-10:50", "11:00-11:50", "12:00-12:50", "1:40-2:30", "2:40-3:30", "3:40-4:30"]

# Convert DataFrames to dictionaries
ROOMS = dict(zip(sections_df['Section'], sections_df['Room']))
SUBJECTS = subjects_df['Subject'].unique().tolist()

# Create SUBJECT_HOURS and TEACHERS dictionaries
SUBJECT_HOURS = {}
TEACHERS = {}
for _, row in subjects_df.iterrows():
    SUBJECT_HOURS[row['Subject']] = row['Hours']
    TEACHERS[row['Subject']] = row['Teachers'].split(',')

LAB_ROOMS = rooms_df[rooms_df['Type'] == 'Lab']['Room'].tolist()

# Parameters
POPULATION_SIZE = 10
GENERATIONS = 100
MUTATION_RATE = 0.01

# Genome representation: List of tuples (day, time, section, subject, teacher, room)
Genome = List[Tuple[str, str, str, str, str, str]]

def generate_genome() -> Genome:
    genome = []
    subject_hours_remaining = {section: SUBJECT_HOURS.copy() for section in ROOMS.keys()}
    teacher_assignment = {section: {} for section in ROOMS.keys()}
    
    for section in ROOMS.keys():
        labs_scheduled = set()
        for day in DAYS:
            day_subjects = set()
            for time in TIMES:
                if not any(subject_hours_remaining[section].values()):
                    genome.append((day, time, section, "Free", "N/A", ROOMS[section]))
                    continue
                
                available_subjects = [subject for subject, hours in subject_hours_remaining[section].items() if hours > 0 and subject not in day_subjects]
                
                if not available_subjects:
                    genome.append((day, time, section, "Free", "N/A", ROOMS[section]))
                    continue
                
                subject = random.choice(available_subjects)
                
                if subject in teacher_assignment[section]:
                    teacher = teacher_assignment[section][subject]
                else:
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
                
                if subject.endswith("Lab"):
                    if subject not in labs_scheduled and subject_hours_remaining[section][subject] == 2 and time not in TIMES[-1:]:
                        lab_room = random.choice(LAB_ROOMS)
                        genome.append((day, time, section, subject, teacher, lab_room))
                        genome.append((day, TIMES[TIMES.index(time) + 1], section, subject, teacher, lab_room))
                        subject_hours_remaining[section][subject] -= 2
                        labs_scheduled.add(subject)
                        break
                else:
                    genome.append((day, time, section, subject, teacher, ROOMS[section]))
                    subject_hours_remaining[section][subject] -= 1
                    day_subjects.add(subject)
    
    for section in ROOMS.keys():
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
    
    for section in ROOMS.keys():
        section_timetable = [entry for entry in genome if entry[2] == section]
        
        for day in DAYS:
            daily_schedule = [entry for entry in section_timetable if entry[0] == day]
            subjects_today = [entry[3] for entry in daily_schedule if not entry[3].endswith("Lab")]
            if len(subjects_today) != len(set(subjects_today)):
                fitness -= 10
        
        for day in DAYS:
            daily_schedule = [entry for entry in section_timetable if entry[0] == day]
            for i in range(len(daily_schedule) - 1):
                if daily_schedule[i][3].endswith("Lab") and daily_schedule[i+1][3].endswith("Lab"):
                    if daily_schedule[i][3] == daily_schedule[i+1][3] and daily_schedule[i][5] == daily_schedule[i+1][5]:
                        continue
                    else:
                        fitness -= 10
        
        for entry in section_timetable:
            if not entry[3].endswith("Lab") and entry[5] != ROOMS[section]:
                fitness -= 5
        
        for day in DAYS:
            daily_schedule = [entry for entry in section_timetable if entry[0] == day]
            if all(entry[3] == "Free" for entry in daily_schedule):
                fitness -= 5
        
    return fitness

def select_parents(population: List[Genome]) -> Tuple[Genome, Genome]:
    fitness_scores = [(genome, calculate_fitness(genome)) for genome in population]
    fitness_scores.sort(key=lambda x: x[1])
    return fitness_scores[-2][0], fitness_scores[-1][0]

def crossover(parent1: Genome, parent2: Genome) -> Tuple[Genome, Genome]:
    point = len(parent1) // 2
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2

def mutate(genome: Genome) -> Genome:
    index = random.randint(0, len(genome) - 1)
    # Generate a new genome and ensure it's of the same length
    new_genome = generate_genome()
    if len(new_genome) > len(genome):
        new_genome = new_genome[:len(genome)]  # Truncate if it's too long
    elif len(new_genome) < len(genome):
        new_genome += generate_genome()[:len(genome) - len(new_genome)]  # Extend if it's too short
    
    genome[index] = new_genome[index]  # Replace with a new random gene
    return genome

def genetic_algorithm() -> Genome:
    population = [generate_genome() for _ in range(POPULATION_SIZE)]
    
    for _ in range(GENERATIONS):
        parent1, parent2 = select_parents(population)
        
        new_population = []
        for _ in range(POPULATION_SIZE // 2):
            child1, child2 = crossover(parent1, parent2)
            
            if random.random() < MUTATION_RATE:
                child1 = mutate(child1)
            if random.random() < MUTATION_RATE:
                child2 = mutate(child2)
            
            new_population.append(child1)
            new_population.append(child2)
        
        population = new_population
    
    best_genome = min(population, key=calculate_fitness)
    return best_genome

def format_timetable(genome: Genome, section: str) -> str:
    timetable = f"Timetable for Section {section}:\n"
    for entry in genome:
        if entry[2] == section:
            timetable += f"{entry[0]} {entry[1]} - {entry[3]} with {entry[4]} in {entry[5]}\n"
    return timetable

# Streamlit app
def main():
    st.title("Timetable Generator")
    
    # Run genetic algorithm
    best_timetable = genetic_algorithm()
    
    # Display timetables for all sections
    for section in ROOMS.keys():
        formatted_timetable = format_timetable(best_timetable, section)
        st.subheader(f"Section {section}")
        st.text(formatted_timetable)

if __name__ == "__main__":
    main()
