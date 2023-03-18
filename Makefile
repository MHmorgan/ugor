
flask:
	flask --debug run -p 8000

run:
	gunicorn -w 4 'app:create_app()'


# Docker

NAME=ugor
ARGS=--rm -p 8000:80 -v $(shell pwd):/data

build:
	docker build --tag $(NAME):dev .

docker:
	docker run $(ARGS) $(NAME):dev
