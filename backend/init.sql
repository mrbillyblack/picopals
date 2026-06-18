-- Schema for long-term save data. Loaded once by the MySQL container on first
-- boot (docker-entrypoint-initdb.d). The backend also create_all()s these on
-- startup so local non-docker runs work too.

CREATE TABLE IF NOT EXISTS users (
    id            CHAR(36)     NOT NULL,
    recovery_code VARCHAR(32)  NOT NULL,
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_recovery_code (recovery_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pets (
    user_id    CHAR(36) NOT NULL,
    state      JSON     NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_pet_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
