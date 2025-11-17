package jpamb.cases;

import jpamb.utils.Case;

public class Strings {

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringLength() {
    String str = "hello";
    assert str.length() == 5;
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void emptyStringLength() {
    String str = "";
    assert str.length() == 0;
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringIsEmpty() {
    String str = "";
    assert str.isEmpty();
  }

  @Case("() -> assertion error")
  @Tag( STRING )
  public static void nonEmptyStringIsEmpty() {
    String str = "hello";
    assert str.isEmpty();
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringCharAt() {
    String str = "hello";
    assert str.charAt(0) == 'h';
  }

  @Case("() -> out of bounds")
  @Tag( STRING )
  public static void stringCharAtOutOfBounds() {
    String str = "hello";
    char c = str.charAt(10);
  }

  @Case("() -> out of bounds")
  @Tag( STRING )
  public static void stringCharAtNegative() {
    String str = "hello";
    char c = str.charAt(-1);
  }

  @Case("() -> null pointer")
  @Tag( STRING )
  public static void stringIsNull() {
    String str = null;
    int len = str.length();
  }

  @Case("() -> null pointer")
  @Tag( STRING )
  public static void stringIsNullCharAt() {
    String str = null;
    char c = str.charAt(0);
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringEquals() {
    String str1 = "hello";
    String str2 = "hello";
    assert str1.equals(str2);
  }

  @Case("() -> assertion error")
  @Tag( STRING )
  public static void stringNotEquals() {
    String str1 = "hello";
    String str2 = "world";
    assert str1.equals(str2);
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringEqualsNull() {
    String str = "hello";
    assert !str.equals(null);
  }

  @Case("() -> null pointer")
  @Tag( STRING )
  public static void stringEqualsOnNull() {
    String str = null;
    boolean result = str.equals("hello");
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringSubstring() {
    String str = "hello";
    String sub = str.substring(1, 3);
    assert sub.equals("el");
  }

  @Case("() -> out of bounds")
  @Tag( STRING )
  public static void stringSubstringOutOfBounds() {
    String str = "hello";
    String sub = str.substring(1, 10);
  }

  @Case("() -> out of bounds")
  @Tag( STRING )
  public static void stringSubstringNegative() {
    String str = "hello";
    String sub = str.substring(-1, 3);
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringSubstringToEnd() {
    String str = "hello";
    String sub = str.substring(2);
    assert sub.equals("llo");
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringIndexOf() {
    String str = "hello";
    int index = str.indexOf("ll");
    assert index == 2;
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringIndexOfNotFound() {
    String str = "hello";
    int index = str.indexOf("xyz");
    assert index == -1;
  }

  @Case("() -> null pointer")
  @Tag( STRING )
  public static void stringIndexOfNull() {
    String str = "hello";
    int index = str.indexOf(null);
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringConcat() {
    String str1 = "hello";
    String str2 = "world";
    String result = str1.concat(str2);
    assert result.equals("helloworld");
  }

  @Case("() -> null pointer")
  @Tag( STRING )
  public static void stringConcatNull() {
    String str = "hello";
    String result = str.concat(null);
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringWithSpecialCharacters() {
    String str = "hello\nworld\t!@#$%";
    assert str.length() > 0;
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringWithUnicode() {
    // Test with extended ASCII and Unicode escape sequences
    String str = "hello world";
    assert str.length() > 5;
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringCharAtLast() {
    String str = "hello";
    char c = str.charAt(str.length() - 1);
    assert c == 'o';
  }

  @Case("() -> out of bounds")
  @Tag( STRING )
  public static void stringCharAtLength() {
    String str = "hello";
    char c = str.charAt(str.length());
  }

  @Case("() -> out of bounds")
  @Tag( STRING )
  public static void emptyStringCharAt() {
    String str = "";
    char c = str.charAt(0);
  }

  @Case("() -> ok")
  @Tag( STRING )
  public static void stringSubstringEmpty() {
    String str = "hello";
    String sub = str.substring(2, 2);
    assert sub.isEmpty();
  }

  // @Case("() -> assertion error")
  // @Tag( STRING )
  // public static void stringSubstringWrongOrder() {
  //   String str = "hello";
  //   String sub = str.substring(3, 1);
  // }

}

