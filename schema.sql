drop table if exists memories;
create table memories (
    id integer primary key autoincrement,
    memory text not null,
    image text 
);
