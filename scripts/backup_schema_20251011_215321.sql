--
-- PostgreSQL database dump
--

\restrict BfRGVun19m6eHvwRL3t0TnzT0xv92efEgdXgN1a6sgbgF9ODCeVogaWMqnIqFJ8

-- Dumped from database version 16.10 (Debian 16.10-1.pgdg13+1)
-- Dumped by pg_dump version 16.10 (Debian 16.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY enem_questions.questions DROP CONSTRAINT IF EXISTS questions_exam_metadata_id_fkey;
ALTER TABLE IF EXISTS ONLY enem_questions.question_images DROP CONSTRAINT IF EXISTS question_images_question_id_fkey;
ALTER TABLE IF EXISTS ONLY enem_questions.question_alternatives DROP CONSTRAINT IF EXISTS question_alternatives_question_id_fkey;
ALTER TABLE IF EXISTS ONLY enem_questions.answer_keys DROP CONSTRAINT IF EXISTS answer_keys_exam_metadata_id_fkey;
DROP TRIGGER IF EXISTS update_exam_metadata_updated_at ON enem_questions.exam_metadata;
DROP TRIGGER IF EXISTS generate_question_exam_id ON enem_questions.questions;
DROP INDEX IF EXISTS enem_questions.idx_question_images_sequence;
DROP INDEX IF EXISTS enem_questions.idx_question_images_question;
ALTER TABLE IF EXISTS ONLY enem_questions.question_images DROP CONSTRAINT IF EXISTS unique_image_per_question;
ALTER TABLE IF EXISTS ONLY enem_questions.questions DROP CONSTRAINT IF EXISTS questions_pkey;
ALTER TABLE IF EXISTS ONLY enem_questions.question_images DROP CONSTRAINT IF EXISTS question_images_pkey;
ALTER TABLE IF EXISTS ONLY enem_questions.question_alternatives DROP CONSTRAINT IF EXISTS question_alternatives_pkey;
ALTER TABLE IF EXISTS ONLY enem_questions.exam_metadata DROP CONSTRAINT IF EXISTS exam_metadata_pkey;
ALTER TABLE IF EXISTS ONLY enem_questions.answer_keys DROP CONSTRAINT IF EXISTS answer_keys_pkey;
ALTER TABLE IF EXISTS enem_questions.answer_keys ALTER COLUMN id DROP DEFAULT;
DROP TABLE IF EXISTS enem_questions.question_images;
DROP VIEW IF EXISTS enem_questions.exam_statistics;
DROP TABLE IF EXISTS enem_questions.question_alternatives;
DROP VIEW IF EXISTS enem_questions.complete_questions;
DROP TABLE IF EXISTS enem_questions.questions;
DROP TABLE IF EXISTS enem_questions.exam_metadata;
DROP SEQUENCE IF EXISTS enem_questions.answer_keys_id_seq;
DROP TABLE IF EXISTS enem_questions.answer_keys;
DROP FUNCTION IF EXISTS enem_questions.update_updated_at_column();
DROP FUNCTION IF EXISTS enem_questions.generate_exam_id();
DROP SCHEMA IF EXISTS enem_questions;
--
-- Name: enem_questions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA enem_questions;


--
-- Name: generate_exam_id(); Type: FUNCTION; Schema: enem_questions; Owner: -
--

CREATE FUNCTION enem_questions.generate_exam_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    max_exam_id INTEGER;
BEGIN
    IF NEW.exam_id IS NULL THEN
        SELECT COALESCE(MAX(exam_id), 0) + 1 INTO max_exam_id FROM questions;
        NEW.exam_id = max_exam_id;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: enem_questions; Owner: -
--

CREATE FUNCTION enem_questions.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: answer_keys; Type: TABLE; Schema: enem_questions; Owner: -
--

CREATE TABLE enem_questions.answer_keys (
    id integer NOT NULL,
    exam_year integer,
    exam_type character varying(50),
    question_number integer,
    correct_answer character(1),
    exam_metadata_id uuid,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: answer_keys_id_seq; Type: SEQUENCE; Schema: enem_questions; Owner: -
--

CREATE SEQUENCE enem_questions.answer_keys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: answer_keys_id_seq; Type: SEQUENCE OWNED BY; Schema: enem_questions; Owner: -
--

ALTER SEQUENCE enem_questions.answer_keys_id_seq OWNED BY enem_questions.answer_keys.id;


--
-- Name: exam_metadata; Type: TABLE; Schema: enem_questions; Owner: -
--

CREATE TABLE enem_questions.exam_metadata (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    year integer,
    exam_type character varying(50),
    application_type character varying(50),
    language character varying(50),
    pdf_filename character varying(255),
    pdf_path text,
    day integer,
    caderno character varying(10),
    file_type character varying(50),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: questions; Type: TABLE; Schema: enem_questions; Owner: -
--

CREATE TABLE enem_questions.questions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    exam_id integer,
    exam_metadata_id uuid,
    question_number integer,
    subject character varying(100),
    competency character varying(255),
    skill character varying(255),
    question_text text,
    image_path text,
    correct_answer character(1),
    explanation text,
    difficulty_level character varying(20),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: complete_questions; Type: VIEW; Schema: enem_questions; Owner: -
--

CREATE VIEW enem_questions.complete_questions AS
 SELECT q.id AS question_id,
    q.exam_id,
    q.question_number,
    q.subject,
    q.competency,
    q.skill,
    q.question_text,
    em.year,
    em.exam_type,
    em.application_type,
    em.language,
    em.day,
    em.caderno,
    ak.correct_answer
   FROM ((enem_questions.questions q
     JOIN enem_questions.exam_metadata em ON ((q.exam_metadata_id = em.id)))
     LEFT JOIN enem_questions.answer_keys ak ON (((em.id = ak.exam_metadata_id) AND (q.question_number = ak.question_number))));


--
-- Name: question_alternatives; Type: TABLE; Schema: enem_questions; Owner: -
--

CREATE TABLE enem_questions.question_alternatives (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    question_id uuid,
    alternative_letter character(1),
    alternative_text text,
    is_correct boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: exam_statistics; Type: VIEW; Schema: enem_questions; Owner: -
--

CREATE VIEW enem_questions.exam_statistics AS
 SELECT em.year,
    em.exam_type,
    em.application_type,
    em.day,
    count(DISTINCT q.id) AS total_questions,
    count(DISTINCT qa.id) AS total_alternatives,
    count(DISTINCT ak.id) AS total_answers,
    count(DISTINCT q.subject) AS total_subjects
   FROM (((enem_questions.exam_metadata em
     LEFT JOIN enem_questions.questions q ON ((em.id = q.exam_metadata_id)))
     LEFT JOIN enem_questions.question_alternatives qa ON ((q.id = qa.question_id)))
     LEFT JOIN enem_questions.answer_keys ak ON ((em.id = ak.exam_metadata_id)))
  GROUP BY em.year, em.exam_type, em.application_type, em.day
  ORDER BY em.year DESC, em.day;


--
-- Name: question_images; Type: TABLE; Schema: enem_questions; Owner: -
--

CREATE TABLE enem_questions.question_images (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    question_id uuid NOT NULL,
    image_sequence integer DEFAULT 1 NOT NULL,
    image_path text,
    image_data bytea,
    image_format character varying(10),
    image_width integer,
    image_height integer,
    image_size_bytes integer,
    extracted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_image_sequence CHECK ((image_sequence >= 1))
);


--
-- Name: answer_keys id; Type: DEFAULT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.answer_keys ALTER COLUMN id SET DEFAULT nextval('enem_questions.answer_keys_id_seq'::regclass);


--
-- Name: answer_keys answer_keys_pkey; Type: CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.answer_keys
    ADD CONSTRAINT answer_keys_pkey PRIMARY KEY (id);


--
-- Name: exam_metadata exam_metadata_pkey; Type: CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.exam_metadata
    ADD CONSTRAINT exam_metadata_pkey PRIMARY KEY (id);


--
-- Name: question_alternatives question_alternatives_pkey; Type: CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.question_alternatives
    ADD CONSTRAINT question_alternatives_pkey PRIMARY KEY (id);


--
-- Name: question_images question_images_pkey; Type: CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.question_images
    ADD CONSTRAINT question_images_pkey PRIMARY KEY (id);


--
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- Name: question_images unique_image_per_question; Type: CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.question_images
    ADD CONSTRAINT unique_image_per_question UNIQUE (question_id, image_sequence);


--
-- Name: idx_question_images_question; Type: INDEX; Schema: enem_questions; Owner: -
--

CREATE INDEX idx_question_images_question ON enem_questions.question_images USING btree (question_id);


--
-- Name: idx_question_images_sequence; Type: INDEX; Schema: enem_questions; Owner: -
--

CREATE INDEX idx_question_images_sequence ON enem_questions.question_images USING btree (image_sequence);


--
-- Name: questions generate_question_exam_id; Type: TRIGGER; Schema: enem_questions; Owner: -
--

CREATE TRIGGER generate_question_exam_id BEFORE INSERT ON enem_questions.questions FOR EACH ROW EXECUTE FUNCTION enem_questions.generate_exam_id();


--
-- Name: exam_metadata update_exam_metadata_updated_at; Type: TRIGGER; Schema: enem_questions; Owner: -
--

CREATE TRIGGER update_exam_metadata_updated_at BEFORE UPDATE ON enem_questions.exam_metadata FOR EACH ROW EXECUTE FUNCTION enem_questions.update_updated_at_column();


--
-- Name: answer_keys answer_keys_exam_metadata_id_fkey; Type: FK CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.answer_keys
    ADD CONSTRAINT answer_keys_exam_metadata_id_fkey FOREIGN KEY (exam_metadata_id) REFERENCES enem_questions.exam_metadata(id);


--
-- Name: question_alternatives question_alternatives_question_id_fkey; Type: FK CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.question_alternatives
    ADD CONSTRAINT question_alternatives_question_id_fkey FOREIGN KEY (question_id) REFERENCES enem_questions.questions(id);


--
-- Name: question_images question_images_question_id_fkey; Type: FK CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.question_images
    ADD CONSTRAINT question_images_question_id_fkey FOREIGN KEY (question_id) REFERENCES enem_questions.questions(id) ON DELETE CASCADE;


--
-- Name: questions questions_exam_metadata_id_fkey; Type: FK CONSTRAINT; Schema: enem_questions; Owner: -
--

ALTER TABLE ONLY enem_questions.questions
    ADD CONSTRAINT questions_exam_metadata_id_fkey FOREIGN KEY (exam_metadata_id) REFERENCES enem_questions.exam_metadata(id);


--
-- PostgreSQL database dump complete
--

\unrestrict BfRGVun19m6eHvwRL3t0TnzT0xv92efEgdXgN1a6sgbgF9ODCeVogaWMqnIqFJ8

