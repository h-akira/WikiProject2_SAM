import random
import base64

def gen_code(length):
  allow="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
  return ''.join(random.choice(allow) for i in range(length))

class Shogi:
  ## coordinate
  # 座標
  # 6iなどで、1文字目は1-9、2文字目はa-i
  ## koma
  # 駒
  # 先手が大文字、後手が小文字
  # K: 玉
  # R: 飛車
  # B: 角
  # G: 金
  # S: 銀
  # N: 桂
  # L: 香
  # P: 歩
  # +: 成り
  ## turn
  # 手番
  # b: 先手
  # w: 後手
  kansuuji_list = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
  kanji_dic = {
    "K": "玉",
    "R": "飛",
    "B": "角",
    "G": "金",
    "S": "銀",
    "N": "桂",
    "L": "香",
    "P": "歩",
    "+R": "龍",
    "+B": "馬",
    "+S": "成銀",
    "+N": "成桂",
    "+L": "成香",
    "+P": "と",
    "k": "玉",
    "r": "飛",
    "b": "角",
    "g": "金",
    "s": "銀",
    "n": "桂",
    "l": "香",
    "p": "歩",
    "+r": "龍",
    "+b": "馬",
    "+s": "成銀",
    "+n": "成桂",
    "+l": "成香",
    "+p": "と"
  }
  def __init__(self, position_sfen):
    onBoard, self.turn, inHand, count = position_sfen.split(" ")
    sfen_rows = onBoard.split("/")
    if len(sfen_rows) != 9:
      raise ValueError("Invalid SFEN")
    self.onBoard = []
    for sfen_row in sfen_rows:
      row = []
      nari_flag = False
      for v in list(sfen_row):
        if v in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
          row.extend([None] * int(v))
        elif v == "+":
          nari_flag = True
        else:
          if nari_flag:
            row.append("+" + v)
            nari_flag = False
          else:
            row.append(v)
      self.onBoard.append(row)
    self.inHand = {
      "R": 0,
      "B": 0,
      "G": 0,
      "S": 0,
      "N": 0,
      "L": 0,
      "P": 0,
      "r": 0,
      "b": 0,
      "g": 0,
      "s": 0,
      "n": 0,
      "l": 0,
      "p": 0
    }
    if inHand != "-":
      number = ""
      for w in list(inHand):
        if w in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
          number += w
        else:
          if number == "":
            self.inHand[w] = 1
          else:
            self.inHand[w] = int(number)
            number = ""
    self.count = int(count)

  def show(self):
    for row in self.onBoard:
      row_str = ""
      for v in row:
        if v is None:
          row_str += ".\t"
        else:
          row_str += (v + "\t")
      print(row_str[:-1])
    print("手番: " + self.turn)
    print("持ち駒: "+ str(self.inHand))

  def move_by_sfen_move(self, sfen_move: str, return_kifu_jp = False):
    # self.show()
    # print(f"sfen_move: {sfen_move}")
    if sfen_move.__class__ != str:
      raise TypeError("sfen_move must be str")
    if len(sfen_move) == 5 and sfen_move[-1] == "+":
      nari = True
    elif len(sfen_move) == 4:
      nari = False
    else:
      print("-------------------------------------")
      print(f"sfen_move: {sfen_move}")
      print("-------------------------------------")
      raise ValueError("sfen_move must be 4 characters or 5 characters")
    before_coordinate = sfen_move[:2]
    after_coordinate = sfen_move[2:4]
    i, j = self._coordinate2index(before_coordinate)
    k, l = self._coordinate2index(after_coordinate)
    # 手番側の駒を除去
    if j == "*":
      koma = i
      if self.turn == "w":
        koma = koma.lower()
      if self.inHand[koma] == 0:
        raise ValueError("inHand must be > 0")
      self.inHand[koma] -= 1
    else:
      koma = self.onBoard[i][j]
      self.onBoard[i][j] = None
    # 駒を取る場合
    if self.onBoard[k][l] is not None:
      got_koma = self.onBoard[k][l]
      if got_koma[0] == "+":
        got_koma = got_koma[1:]
      if self.turn == "b":
        if got_koma.islower():
          got_koma = got_koma.upper()
        else:
          raise ValueError("got_koma is not your koma")
      elif self.turn == "w":
        if got_koma.isupper():
          got_koma = got_koma.lower()
        else:
          # print(got_koma)
          raise ValueError("got_koma is not your koma")
      else:
        raise ValueError("turn must be b or w")
      self.inHand[got_koma] += 1
    # 駒を動かす
    if nari:
      if koma[0] == "+":
        raise ValueError("koma is already nari")
      else:
        self.onBoard[k][l] = "+" + koma
    else:
      self.onBoard[k][l] = koma
    # 手番と手数の更新
    if self.turn == "b":
      self.turn = "w"
    else:
      self.turn = "b"
    self.count += 1
    # 返り値
    if return_kifu_jp:
      kifu_jp = ""
      # 先手か後手かだが、すでに手番が変わっているので、逆にする
      if self.turn == "b":
        kifu_jp += "△"
      elif self.turn == "w":
        kifu_jp += "▲"
      else:
        raise ValueError("turn must be b or w")
      # kifu_jp += str(l+1)
      kifu_jp += str(9-l)
      # kifu_jp += self.__class__.kansuuji_list[8-k]
      kifu_jp += self.__class__.kansuuji_list[k]
      kifu_jp += self.__class__.kanji_dic[koma]
      if nari:
        kifu_jp += "成"
      if j == "*":
        kifu_jp += "(--)"
      else:
        # kifu_jp += f"({j+1}{9-i})"
        kifu_jp += f"({9-j}{i+1})"
      return kifu_jp
  def _coordinate2index(self, coordinate):
    if coordinate.__class__ != str:
      raise TypeError("coordinate must be str")
    if len(coordinate) != 2:
      raise ValueError("coordinate must be 2 characters")
    if coordinate[1] == "*":
      if coordinate[0] not in ["P", "L", "N", "S", "G", "B", "R", "K"]:
        raise ValueError("coordinate must be P, L, N, S, G, B, R, K")
      return coordinate[0], coordinate[1]
    else:
      return ord(coordinate[1]) - ord("a"), 9-int(coordinate[0])
  def moves_by_sfen_moves(self, sfen_moves: list, return_kifu_jp_list = False, same=True):
    if sfen_moves.__class__ != list:
      raise TypeError("sfen_moves must be list")
    if return_kifu_jp_list:
      kifu_jp_list = []
    for move in sfen_moves:
      kifu_jp = self.move_by_sfen_move(move, return_kifu_jp=return_kifu_jp_list)
      if return_kifu_jp_list:
        kifu_jp_list.append(kifu_jp)
    if same:
      for i in range(len(kifu_jp_list)-1):
        if kifu_jp_list[len(kifu_jp_list)-1-i][1:3] == kifu_jp_list[len(kifu_jp_list)-2-i][1:3]:
          kifu_jp_list[len(kifu_jp_list)-1-i] = kifu_jp_list[len(kifu_jp_list)-1-i][0]+"同"+kifu_jp_list[len(kifu_jp_list)-1-i][3:]
    if return_kifu_jp_list:
      return kifu_jp_list

def encode_for_url(text):
    return base64.urlsafe_b64encode(text.encode('utf-8')).decode('ascii').rstrip("=")

def decode_from_url(encoded):
    padding = '=' * ((4 - len(encoded) % 4) % 4)
    return base64.urlsafe_b64decode((encoded + padding).encode('ascii')).decode('utf-8')

# def main():
#   SFEN = "lnsgkgsnl/1r5b1/p1pppp1p1/6p1p/9/2P6/PP1PPPPPP/1B5R1/LNSGKGSNL b - 1"
#   sashite = "7f7e 7a7b 1g1f 5a4b 6i7h 7b8c 2g2f 8c8d 2f2e 8d7e 2e2d 2c2d 2h2d 4a3b 2d2h P*2c".split(" ")
#   shogi = Shogi(SFEN)
#   kifu_jp_list = shogi.moves_by_sfen_moves(sashite, return_kifu_jp_list=True)
#   print(kifu_jp_list)
#
# if __name__ == "__main__":
#   main()
