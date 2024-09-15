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
TIMES = ["9:00-9:50", "10:00-10:50", "11:00-11:50",
         "12:00-12:50", "1:40-2:30", "2:40-3:30", "3:40-4:30"]

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
Gene = Tuple[str, str, str, str, str, str]
Genome = List[Gene]


def generate_genome() -> Genome:
    genome = []
    subject_hours_remaining = {
        section: SUBJECT_HOURS.copy() for section in ROOMS.keys()}
    teacher_assignment = {section: {} for section in ROOMS.keys()}

    for section in ROOMS.keys():
        labs_scheduled = set()
        for day in DAYS:
            day_subjects = set()
            for time in TIMES:
                if not any(subject_hours_remaining[section].values()):
                    genome.append(
                        (day, time, section, "Free", "N/A", ROOMS[section]))
                    continue

                available_subjects = [subject for subject, hours in subject_hours_remaining[section].items(
                ) if hours > 0 and subject not in day_subjects]

                if not available_subjects:
                    genome.append(
                        (day, time, section, "Free", "N/A", ROOMS[section]))
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
                    if subject not in labs_scheduled and subject_hours_remaining[section][subject] >= 2 and time != TIMES[-1]:
                        time_index = TIMES.index(time)
                        next_time = TIMES[time_index + 1]
                        lab_room = random.choice(LAB_ROOMS)
                        genome.append(
                            (day, time, section, subject, teacher, lab_room))
                        genome.append(
                            (day, next_time, section, subject, teacher, lab_room))
                        subject_hours_remaining[section][subject] -= 2
                        labs_scheduled.add(subject)
                        break  # Skip next time slot
                    else:
                        genome.append(
                            (day, time, section, "Free", "N/A", ROOMS[section]))
                else:
                    genome.append(
                        (day, time, section, subject, teacher, ROOMS[section]))
                    subject_hours_remaining[section][subject] -= 1
                    day_subjects.add(subject)

        # Fill any remaining slots with "Free"
        total_slots = len(DAYS) * len(TIMES)
        if len([gene for gene in genome if gene[2] == section]) < total_slots:
            for day in DAYS:
                for time in TIMES:
                    if not any(gene for gene in genome if gene[2] == section and gene[0] == day and gene[1] == time):
                        genome.append(
                            (day, time, section, "Free", "N/A", ROOMS[section]))
    return genome


def calculate_fitness(genome: Genome) -> int:
    fitness = 0

    for section in ROOMS.keys():
        section_timetable = [entry for entry in genome if entry[2] == section]

        # Constraint: No subject repeats more than once per day (except labs)
        for day in DAYS:
            daily_schedule = [
                entry for entry in section_timetable if entry[0] == day]
            subjects_today = [entry[3] for entry in daily_schedule if not entry[3].endswith("Lab") and entry[3] != "Free"]
            if len(subjects_today) != len(set(subjects_today)):
                fitness -= 10

        # Constraint: Labs should be scheduled consecutively
        for day in DAYS:
            daily_schedule = sorted(
                [entry for entry in section_timetable if entry[0] == day], key=lambda x: TIMES.index(x[1]))
            for i in range(len(daily_schedule) - 1):
                current = daily_schedule[i]
                next_slot = daily_schedule[i + 1]
                if current[3].endswith("Lab"):
                    if not (next_slot[3] == current[3] and next_slot[5] == current[5]):
                        fitness -= 5

        # Constraint: Correct room assignments
        for entry in section_timetable:
            subject, room = entry[3], entry[5]
            if subject.endswith("Lab") and room not in LAB_ROOMS:
                fitness -= 5
            elif not subject.endswith("Lab") and room != ROOMS[section]:
                fitness -= 5

        # Constraint: No full day free
        for day in DAYS:
            daily_schedule = [
                entry for entry in section_timetable if entry[0] == day]
            if all(entry[3] == "Free" for entry in daily_schedule):
                fitness -= 10

    return fitness


def select_parents(population: List[Genome]) -> Tuple[Genome, Genome]:
    fitness_scores = sorted(population, key=calculate_fitness, reverse=True)
    return fitness_scores[0], fitness_scores[1]


def crossover(parent1: Genome, parent2: Genome) -> Tuple[Genome, Genome]:
    point = random.randint(1, len(parent1) - 2)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]
    return child1, child2


def mutate(genome: Genome) -> Genome:
    mutated_genome = genome.copy()
    index = random.randint(0, len(genome) - 1)
    day, time, section, _, _, _ = mutated_genome[index]

    available_subjects = SUBJECTS + ["Free"]
    subject = random.choice(available_subjects)

    if subject == "Free":
        teacher = "N/A"
        room = ROOMS[section]
    elif subject.endswith("Lab"):
        teacher = random.choice(TEACHERS[subject])
        room = random.choice(LAB_ROOMS)
    else:
        teacher = random.choice(TEACHERS[subject])
        room = ROOMS[section]

    mutated_genome[index] = (day, time, section, subject, teacher, room)
    return mutated_genome


def genetic_algorithm() -> Genome:
    population = [generate_genome() for _ in range(POPULATION_SIZE)]

    for _ in range(GENERATIONS):
        new_population = []
        for _ in range(POPULATION_SIZE // 2):
            parent1, parent2 = select_parents(population)
            child1, child2 = crossover(parent1, parent2)

            if random.random() < MUTATION_RATE:
                child1 = mutate(child1)
            if random.random() < MUTATION_RATE:
                child2 = mutate(child2)

            new_population.extend([child1, child2])

        population = new_population

    best_genome = max(population, key=calculate_fitness)
    return best_genome


def format_timetable(genome: Genome, section: str) -> pd.DataFrame:
    # Create an empty DataFrame with TIMES as rows and DAYS as columns
    timetable_df = pd.DataFrame(index=TIMES, columns=DAYS)

    # Filter genes for the specific section
    section_genes = [gene for gene in genome if gene[2] == section]

    # Populate the DataFrame
    for gene in section_genes:
        day = gene[0]
        time = gene[1]
        subject = gene[3]
        teacher = gene[4]
        room = gene[5]
        if subject == "Free":
            cell_content = "Free"
        else:
            cell_content = f"{subject}\n{teacher}\n{room}"
        timetable_df.at[time, day] = cell_content

    return timetable_df


def main():
    st.title("Timetable Generator")

    # Run genetic algorithm
    best_timetable = genetic_algorithm()

    # Display timetables for all sections
    for section in sorted(ROOMS.keys()):
        st.header(f"Section {section}")
        timetable_df = format_timetable(best_timetable, section)
        st.table(timetable_df)


if __name__ == "__main__":
    main()
