import rg
import random

#Zwraca true jesli lokacja jest na planszy
def is_valid_location(loc):
    loc_types = rg.loc_types(loc)
    return "invalid" not in loc_types and "obstacle" not in loc_types


#Zwraca true jesli lokacja jest na spawnie
def is_spawn_location(loc):
    loc_types = rg.loc_types(loc)
    return "spawn" in loc_types


#Zwraca lokalizacje otaczajace podana w argumencie lokalizacje
def surround_locations(loc):
    if loc is None:
        return []
    x = loc[0]
    y = loc[1]
    slocs = []
    slocs.append((x, y - 1))  # up
    slocs.append((x, y + 1))  # down
    slocs.append((x + 1, y))  # right
    slocs.append((x - 1, y))  # left

    return [l for l in slocs if is_valid_location(l)]


#Zwraca centroid dla lokalizacji
def centroid_location(locs):
    x = [p[0] for p in locs]
    y = [p[1] for p in locs]
    centroid = (sum(x) / len(locs), sum(y) / len(locs))
    return centroid


#Zwraca liste niebezpiecznych lokalizacji (ryzyko kolizji oraz walki)
def unsafe_locations(enemies_locs):
    unsafe_locs = []
    for enemy_loc in enemies_locs:
        unsafe_locs += surround_locations(enemy_loc)

    unsafe_locs += enemies_locs
    return list(set(unsafe_locs))


#Sprawdza czy robot jest okrazony przez przynajmniej 2 przeciwnikow
def is_surrounded(loc, enemies_locs):
    robot_moves = surround_locations(loc)

    enemies_surround = 0
    for loc in enemies_locs:
        if loc in robot_moves:
            enemies_surround += 1

    return enemies_surround >= 2


def nearest_loc(my_loc, locs):
    min_distance = 999
    nearest = None

    for loc in locs:
        distance = rg.dist(my_loc, loc)
        if distance < min_distance:
            min_distance = distance
            nearest = loc
    return nearest


class Robot():
    def log(self, msg):
        print "({0},{1}) => {2}".format(self.location[0], self.location[1], msg)

    def enemies(self, game):
        robots = []
        for robot in game.robots.values():
            if robot.player_id != self.player_id:
                robots.append(robot)
        return robots

    def allies(self, game):
        robots = []
        for robot in game.robots.values():
            if robot.player_id == self.player_id:
                robots.append(robot)
        return robots

    def act(self, game):
        centroid_loc = centroid_location([r.location for r in self.allies(game)])
        unsafe_locs = unsafe_locations([r.location for r in self.enemies(game)])
        possible_moves = surround_locations(self.location)
        enemies_locs = [r.location for r in self.enemies(game)]
        allies_locs = [r.location for r in self.allies(game)]


        if((game.turn % 11 >= 7) and is_spawn_location(self.location)):
            self.log("Zostaly trzy rundy do kolejnego respawnu, musze uciekac")
            to_center_move = rg.toward(self.location, rg.CENTER_POINT)
            if to_center_move in enemies_locs:
                #przeciwnik blokuje ucieczke :D
                self.log("przeciwnik blokuje mi droge ucieczki!")
                escape_moves = list(set(possible_moves) - set([to_center_move]))
                possible_escape_moves = list(set(escape_moves) - set(enemies_locs))
                if len(possible_escape_moves) > 0:
                    self.log("uciekam w kierunku najblizej srodka")
                    return ['move', nearest_loc(rg.CENTER_POINT, possible_escape_moves)]
            else:
                return ['move', to_center_move]



        #jesli nie ma przeciwnikow
        if len(enemies_locs) == 0:
            self.log("nie ma przeciwnikow - ide na srodek")
            return ['move', rg.toward(self.location, rg.CENTER_POINT)]

        #Unikaj otaczania
        if is_surrounded(self.location, enemies_locs):
            if self.hp < 10:
                self.log("zostalem otoczony ale moje hp jest mniejsze od 10 wiec robie suicide")
                return ['suicide']
            else:
                for pm in possible_moves:
                    if pm not in list(unsafe_locs + allies_locs):
                        self.log("zostalem otoczony! uciekam")
                        return ['move', pm]

        target_enemy_loc = nearest_loc(self.location, enemies_locs)

        target_surround_locs = surround_locations(target_enemy_loc)
        surround_points = []
        bots_fighting_with_enemy = 0
        for sloc in target_surround_locs:
            if sloc in allies_locs:
                bots_fighting_with_enemy += 1
                surround_points.append(sloc)

        if bots_fighting_with_enemy >= 1 and bots_fighting_with_enemy < 4:
            if self.location not in target_surround_locs:
                #Pomagaj sojusznika w walce
                self.log("jeden z naszych sojusznikow potrzebuje pomocy")
                free_surround_points = list(set(target_surround_locs) - set(allies_locs))
                if len(free_surround_points) >= 1:
                    step = rg.toward(self.location, free_surround_points[0])
                    if self.location != step and step not in  allies_locs:
                        self.log("ruszam na pomoc do {0}".format(target_enemy_loc))
                        return ['move', step]
                    elif step in allies_locs:
                        next_mvs = list(set(possible_moves) - set(unsafe_locs) - set(allies_locs))
                        if len(next_mvs) >=1:
                            target_nearest = nearest_loc(target_enemy_loc, next_mvs)
                            if not is_spawn_location(target_nearest):
                                self.log("na drodze do {0} stoi nasz sojusznik - omijamy go {1}".format(target_enemy_loc, repr(next_mvs)))
                                return ['move', target_nearest]


        step = rg.toward(self.location, target_enemy_loc)
        if self.location != step and step not in unsafe_locs:
            self.log("ruszam do ataku na {0}".format(target_enemy_loc))
            return ['move', step]

        #Jesli ja i jakis inny bot otaczamy przeciwnika
        for e_loc in enemies_locs:
            if(is_surrounded(e_loc, allies_locs) and self.location in surround_locations(e_loc)):
                self.log("atak otoczonego przeciwnika")
                return ['attack', e_loc]

        for enemy in self.enemies(game):
            if rg.wdist(self.location, enemy.location) <= 1:
                self.log("atakuje przeciwnika obok")
                return ['attack', enemy.location]

        possible_enemy_moves = list(set(possible_moves) & set(unsafe_locs))
        if len(possible_enemy_moves) > 0:
            self.log("atakuje prawdopodobne miejsce pojawienia sie przeciwnika")
            return ['attack', random.choice(possible_enemy_moves)]




        self.log("atakuje losowo")
        return ['attack', random.choice(list(set(possible_moves)-set(allies_locs)))]
