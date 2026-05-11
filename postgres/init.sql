-- Создание базы данных
CREATE DATABASE appdb;

\c appdb;

-- Таблица опросов
CREATE TABLE IF NOT EXISTS surveys (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица голосов
CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    survey_id INTEGER REFERENCES surveys(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    choice VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(survey_id, user_id)
);

-- Индексы для производительности
CREATE INDEX idx_votes_survey_id ON votes(survey_id);
CREATE INDEX idx_votes_user_id ON votes(user_id);
CREATE INDEX idx_surveys_created_at ON surveys(created_at);

-- Тестовые данные для демонстрации
INSERT INTO surveys (title, description) VALUES 
    ('Любимый язык программирования', 'Какой язык вы предпочитаете?'),
    ('Удобство работы с Docker', 'Насколько вам удобно работать с Docker?')
ON CONFLICT DO NOTHING;