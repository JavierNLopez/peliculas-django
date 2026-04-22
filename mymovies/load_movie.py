import os
import environ
import requests
import psycopg2
from datetime import datetime, date, timezone
import sys


def add_movie(movie_id):
    env = environ.Env()
    environ.Env.read_env('.env')

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {env('API_TOKEN')}"
    }

    # 🎬 Movie data
    r = requests.get(
        f'https://api.themoviedb.org/3/movie/{movie_id}?language=en-US',
        headers=headers
    )
    m = r.json()

    conn = psycopg2.connect(dbname='django', host='/tmp')
    cur = conn.cursor()

    # 🔎 Check if movie exists (USING tmdb_id)
    cur.execute(
        'SELECT id FROM movies_movie WHERE tmdb_id = %s',
        (movie_id,)
    )
    if cur.fetchone():
        print("⚠️ Movie already exists, skipping...")
        return

    # 🎭 Credits
    r = requests.get(
        f'https://api.themoviedb.org/3/movie/{movie_id}/credits?language=en-US',
        headers=headers
    )
    credits = r.json()

    actors = [(actor['name'], actor['known_for_department'])
              for actor in credits['cast'][:10]]

    crew = [(job['name'], job['job'])
            for job in credits['crew'][:15]]

    credits_list = actors + crew

    # 🧑‍💼 Jobs
    jobs = list(set(job for _, job in credits_list))

    cur.execute(
        'SELECT id, name FROM movies_job WHERE name IN %s',
        (tuple(jobs),)
    )
    jobs_in_db = cur.fetchall()

    jobs_to_create = [
        (name,) for name in jobs
        if name not in [j[1] for j in jobs_in_db]
    ]

    cur.executemany(
        'INSERT INTO movies_job (name) VALUES (%s)',
        jobs_to_create
    )

    # 👤 Persons
    persons = list(set(person for person, _ in credits_list))

    cur.execute(
        'SELECT id, name FROM movies_person WHERE name IN %s',
        (tuple(persons),)
    )
    persons_in_db = cur.fetchall()

    persons_to_create = [
        (name,) for name in persons
        if name not in [p[1] for p in persons_in_db]
    ]

    cur.executemany(
        'INSERT INTO movies_person (name) VALUES (%s)',
        persons_to_create
    )

    # 🎬 Genres
    genres = [g['name'] for g in m['genres']]

    cur.execute(
        'SELECT id, name FROM movies_genre WHERE name IN %s',
        (tuple(genres),)
    )
    genres_in_db = cur.fetchall()

    genres_to_create = [
        (name,) for name in genres
        if name not in [g[1] for g in genres_in_db]
    ]

    cur.executemany(
        'INSERT INTO movies_genre (name) VALUES (%s)',
        genres_to_create
    )

    # 📅 Date
    date_obj = date.fromisoformat(m['release_date'])
    date_time = datetime.combine(date_obj, datetime.min.time())

    # 🎬 Insert movie (ONLY ONCE)
    cur.execute('''
        INSERT INTO movies_movie 
        (title, overview, release_date, running_time,
         budget, tmdb_id, revenue, poster_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        m['title'],
        m['overview'],
        date_time.astimezone(timezone.utc),
        m['runtime'],
        m['budget'],
        movie_id,
        m['revenue'],
        m['poster_path']
    ))

    # 🔗 Movie - Genres relation (USING tmdb_id)
    cur.execute('''
        INSERT INTO movies_movie_genres (movie_id, genre_id)
        SELECT m.id, g.id
        FROM movies_movie m
        JOIN movies_genre g ON g.name IN %s
        WHERE m.tmdb_id = %s
    ''', (tuple(genres), movie_id))

    # 🎭 Credits insert
    for person, job in credits_list:
        cur.execute('''
            INSERT INTO movies_moviecredit (movie_id, person_id, job_id)
            SELECT m.id,
                   (SELECT id FROM movies_person WHERE name = %s),
                   (SELECT id FROM movies_job WHERE name = %s)
            FROM movies_movie m
            WHERE m.tmdb_id = %s
        ''', (person, job, movie_id))

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    add_movie(int(sys.argv[1]))
