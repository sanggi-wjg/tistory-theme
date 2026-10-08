# 락 순서를 맞춰 MySQL 데드락 피하기

업무에서 자주 있는 상황은 아니다 보니 막상 개념은 알고 있어도 로직을 짤 때는 종종 까먹곤 한다.
개발팀에서도 이 개념이 익숙하지 않은 분이 있어서 이번 기회에 글로 정리해 둔다.
이 글을 읽고 비슷한 상황을 만났을 때 소위 우아하게 다룰 수 있으면 좋겠다.

## 설명 기준
- MySQL 8.0 이상
- InnoDB 엔진
- Isolation Level: REPEATABLE READ 

## 여러 행을 차례로 잠그는 로직에서는 항상 정렬을 해야 한다
> When modifying multiple tables within a transaction, or different sets of rows in the same table, 
> do those operations in a consistent order each time. Then transactions form well-defined queues and do not deadlock.

MySQL에서는 UPDATE 쿼리나 SELECT ... FOR UPDATE 쿼리가 스캔한 행(들)에 레코드 락을 걸어 
트랜잭션 커밋 전까지는 다른 트랜잭션이 수정/잠금을 못 하도록 한다. 이 때문에 여러 행 수정이 필요한 경우 반드시 주의해야 한다.
(스캔된 행은 변경 대상이 아니어도 전부 잠긴다. 애플리케이션 로직은 주로 PK 기준으로 동작해 범위 업데이트가 많지 않지만, 마이그레이션처럼 업데이트 쿼리로 넓은 범위를 갱신할 때는 반드시 이 점을 주의해야 한다.)

공식 문서도 여러 테이블이나 여러 행을 수정할 때 항상 일관된 순서를 권장하며, 그렇게 하면 트랜잭션들이 차례로 줄을 설 뿐 데드락은 발생하지 않는다고 설명한다.

어떠한 상황에서 데드락이 발생하는지 보자.

[lock-order-deadlock 이미지]

위 이미지처럼 각 트랜잭션이 서로 기다리느라 데드락이 발생한다. 이때 InnoDB는 데드락을 감지해 한쪽 트랜잭션을 통째로 롤백한다.

```
ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction
```

> When deadlock detection is enabled (the default), InnoDB automatically detects transaction deadlocks and rolls back a transaction or transactions to break the deadlock. 
> InnoDB tries to pick small transactions to roll back, where the size of a transaction is determined by the number of rows inserted, updated, or deleted.

반대로 항상 같은 순서로 정렬을 한다면 아래 경우처럼 정상적으로 동작할 수 있다.
단, 같은 행을 잠그는 로직이 모두 같은 순서를 지켜야 한다. 한 곳이라도 다른 순서로 잠그면 다시 데드락이 날 수 있다.

[lock-order-sorted 이미지]

다만 일관된 순서를 보장한다고 해도 문제가 없는 건 아니다. 잠긴 행을 기다리는 시간이 innodb_lock_wait_timeout(기본 50초)을 넘기면 아래 오류가 발생한다.

```
ERROR 1205 (HY000): Lock wait timeout exceeded; try restarting transaction
```

이때 롤백되는 건 마지막 문장뿐이고 트랜잭션은 열린 채 남는다. 앞서 잡은 락도 그대로 쥐고 있다(innodb_rollback_on_timeout 기본값 OFF).

[innodb_rollback_on_timeout_example 이미지]

왼쪽 세션이 id=100을 잠근 상태에서, 오른쪽 세션은 id=99를 수정한 뒤 id=100을 기다리다 1205를 받았다.
그런데도 id=99의 변경은 그대로 남아 있다. 이대로 commit하면 id=99만 반영된다.

데드락과는 달리 InnoDB가 트랜잭션을 정리해 주지는 않는다.

### 실무에서

이런 상황을 방지하기 위해서 트랜잭션을 일정 청크 단위로 나누거나 API 등의 외부 통신이 트랜잭션 안에 포함되지 않도록 해야 한다.
청크로 나누는 경우 한 개 요청에 대해 부분 실패가 날 수 있기 때문에 이 점을 염두에 두고 설계와 구현이 되어야 한다.

### 참고
- https://dev.mysql.com/doc/refman/8.0/en/innodb-locks-set.html
- https://dev.mysql.com/doc/refman/8.0/en/innodb-deadlock-detection.html
- https://dev.mysql.com/doc/refman/8.0/en/innodb-deadlocks-handling.html
- https://dev.mysql.com/doc/refman/8.0/en/innodb-parameters.html#sysvar_innodb_lock_wait_timeout
- https://dev.mysql.com/doc/refman/8.0/en/innodb-parameters.html#sysvar_innodb_rollback_on_timeout
