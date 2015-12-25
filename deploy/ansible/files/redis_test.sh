#!/bin/bash
case "$1" in
	"local" )
		endpoint=`hostname -s`
	;;
	"sentinel" )
		endpoint='sentinel'
	;;
	"master" )
		endpoint='master'
	;;
	 * )
		exit 0
	;;
esac

redis_url=`curl -L http://192.168.3.254:4001/v2/keys/prod/infrastructure/redis/$endpoint | awk -F '"' '{print $14}'`

redis_host=`echo $redis_url | awk -F ':' '{print $1}'`
redis_port=`echo $redis_url | awk -F ':' '{print $2}'`

redis-cli -h $redis_host -p $redis_port ping | grep -c PONG
