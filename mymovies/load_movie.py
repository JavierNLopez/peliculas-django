import sys
from datetime import date, datetime, timezone

import environ
import psycopg2
import requests


def get_json(url, headers):
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def safe_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def extract_country(place_of_birth):
    if not place_of_birth:
        return None
    parts = [p.strip() for p in place_of_birth.split(",") if p.strip()]
    if parts:
        return parts[-1]
    return None


def add_movie(movie_id):
    env = environ.Env()
    environ.Env.read_env(".env")

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {env('API_TOKEN')}",
    }

    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"
    credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?language=en-US"

    m = get_json(movie_url, headers)
    credits = get_json(credits_url, headers)

    conn = psycopg2.connect(dbname="django", host="/tmp")
    cur = conn.cursor()

    try:
        # 1) Verificar si la película ya existe
        cur.execute(
            "SELECT id FROM movies_movie WHERE tmdb_id = %s",
            (movie_id,)
        )
        existing_movie = cur.fetchone()

        if existing_movie:
            print("⚠️ La película ya existe en la base de datos.")
            return

        # 2) Géneros
        genres = [g["name"] for g in m.get("genres", []) if g.get("name")]

        if genres:
            cur.execute(
                "SELECT id, name FROM movies_genre WHERE name IN %s",
                (tuple(genres),)
            )
            genres_in_db = cur.fetchall()
        else:
            genres_in_db = []

        existing_genre_names = [g[1] for g in genres_in_db]
        genres_to_create = [(name,) for name in genres if name not in existing_genre_names]

        if genres_to_create:
            cur.executemany(
                "INSERT INTO movies_genre (name) VALUES (%s)",
                genres_to_create
            )

        # 3) Créditos básicos
        cast_credits = credits.get("cast", [])[:10]
        crew_credits = credits.get("crew", [])[:15]

        raw_credit_entries = []

        for actor in cast_credits:
            raw_credit_entries.append({
                "tmdb_person_id": actor.get("id"),
                "person_name": actor.get("name"),
                "job_name": actor.get("known_for_department") or "Acting",
            })

        for crew_member in crew_credits:
            raw_credit_entries.append({
                "tmdb_person_id": crew_member.get("id"),
                "person_name": crew_member.get("name"),
                "job_name": crew_member.get("job") or "Crew",
            })

        # 4) Jobs
        jobs = list({
            entry["job_name"] for entry in raw_credit_entries
            if entry["job_name"]
        })

        if jobs:
            cur.execute(
                "SELECT id, name FROM movies_job WHERE name IN %s",
                (tuple(jobs),)
            )
            jobs_in_db = cur.fetchall()
        else:
            jobs_in_db = []

        existing_job_names = [j[1] for j in jobs_in_db]
        jobs_to_create = [(name,) for name in jobs if name not in existing_job_names]

        if jobs_to_create:
            cur.executemany(
                "INSERT INTO movies_job (name) VALUES (%s)",
                jobs_to_create
            )

        # 5) Detalle de personas desde TMDB
        detailed_people = []
        seen_people = set()

        for entry in raw_credit_entries:
            person_name = entry["person_name"]
            tmdb_person_id = entry["tmdb_person_id"]
            job_name = entry["job_name"]

            if not person_name or not tmdb_person_id:
                continue

            key = (person_name, tmdb_person_id, job_name)
            if key in seen_people:
                continue
            seen_people.add(key)

            person_url = f"https://api.themoviedb.org/3/person/{tmdb_person_id}?language=en-US"

            try:
                person_data = get_json(person_url, headers)
            except Exception:
                person_data = {}

            profile_path = person_data.get("profile_path")
            image_url = f"https://image.tmdb.org/t/p/w500{profile_path}" if profile_path else None

            birth_date = safe_date(person_data.get("birthday"))
            place_of_birth = person_data.get("place_of_birth")
            country = extract_country(place_of_birth)
            biography = person_data.get("biography")

            detailed_people.append({
                "person_name": person_name,
                "job_name": job_name,
                "image_url": image_url,
                "birth_date": birth_date,
                "country": country,
                "biography": biography,
            })

        # 6) Personas
        person_names = list({
            entry["person_name"] for entry in detailed_people
            if entry["person_name"]
        })

        if person_names:
            cur.execute(
                "SELECT id, name FROM movies_person WHERE name IN %s",
                (tuple(person_names),)
            )
            persons_in_db = cur.fetchall()
        else:
            persons_in_db = []

        existing_person_names = [p[1] for p in persons_in_db]

        persons_to_create = []
        for entry in detailed_people:
            if entry["person_name"] and entry["person_name"] not in existing_person_names:
                persons_to_create.append((
                    entry["person_name"],
                    entry["birth_date"],
                    entry["country"],
                    entry["image_url"],
                    entry["biography"],
                ))
                existing_person_names.append(entry["person_name"])

        if persons_to_create:
            cur.executemany(
                """
                INSERT INTO movies_person (name, birth_date, country, image_url, biography)
                VALUES (%s, %s, %s, %s, %s)
                """,
                persons_to_create
            )

        # 7) Actualizar personas existentes si les falta info
        for entry in detailed_people:
            cur.execute(
                """
                UPDATE movies_person
                SET
                    birth_date = COALESCE(birth_date, %s),
                    country = COALESCE(country, %s),
                    image_url = COALESCE(image_url, %s),
                    biography = COALESCE(biography, %s)
                WHERE name = %s
                """,
                (
                    entry["birth_date"],
                    entry["country"],
                    entry["image_url"],
                    entry["biography"],
                    entry["person_name"],
                )
            )

        # 8) Insertar película
        release_date = m.get("release_date")
        if release_date:
            date_obj = date.fromisoformat(release_date)
            date_time = datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=timezone.utc)
        else:
            date_time = None

        cur.execute(
            """
            INSERT INTO movies_movie
            (title, overview, release_date, running_time, budget, tmdb_id, revenue, poster_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                m.get("title"),
                m.get("overview", ""),
                date_time,
                m.get("runtime"),
                m.get("budget"),
                movie_id,
                m.get("revenue"),
                m.get("poster_path"),
            )
        )

        movie_db_id = cur.fetchone()[0]
        print(f"✅ Película insertada con id interno: {movie_db_id}")

        # 9) Relación película - géneros
        if genres:
            cur.execute(
                "SELECT id, name FROM movies_genre WHERE name IN %s",
                (tuple(genres),)
            )
            all_genres = cur.fetchall()

            movie_genres_to_create = [(movie_db_id, genre_id) for genre_id, _ in all_genres]

            if movie_genres_to_create:
                cur.executemany(
                    """
                    INSERT INTO movies_movie_genres (movie_id, genre_id)
                    VALUES (%s, %s)
                    """,
                    movie_genres_to_create
                )

        # 10) Relación película - personas - jobs
        for entry in detailed_people:
            person_name = entry["person_name"]
            job_name = entry["job_name"]

            if not person_name or not job_name:
                continue

            cur.execute(
                "SELECT id FROM movies_person WHERE name = %s LIMIT 1",
                (person_name,)
            )
            person_row = cur.fetchone()

            cur.execute(
                "SELECT id FROM movies_job WHERE name = %s LIMIT 1",
                (job_name,)
            )
            job_row = cur.fetchone()

            if not person_row or not job_row:
                continue

            person_id = person_row[0]
            job_id = job_row[0]

            cur.execute(
                """
                SELECT id FROM movies_moviecredit
                WHERE movie_id = %s AND person_id = %s AND job_id = %s
                """,
                (movie_db_id, person_id, job_id)
            )
            existing_credit = cur.fetchone()

            if not existing_credit:
                cur.execute(
                    """
                    INSERT INTO movies_moviecredit (movie_id, person_id, job_id)
                    VALUES (%s, %s, %s)
                    """,
                    (movie_db_id, person_id, job_id)
                )

        conn.commit()
        print("✅ Película, géneros, personas y créditos guardados correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ Error al cargar la película:")
        print(e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python mymovies/load_movie.py <movie_id>")
    else:
        add_movie(int(sys.argv[1]))
