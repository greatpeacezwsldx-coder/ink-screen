import { promptAction } from '@kit.ArkUI';

@Entry
@Component
struct Welcome {
  @State username: string = '';
  @State password: string = '';
  @State showPassword: boolean = false;
  @State errorMsg: string = '';
  @State isLoggedIn: boolean = false;

  build() {
    if (!this.isLoggedIn) {
      this.LoginPage();
    } else {
      this.HomePage();
    }
  }

  @Builder
  LoginPage() {
    Column() {
      // 顶部标题
      Column() {
        Text('智绘相册')
          .fontSize(36)
          .fontWeight(FontWeight.Bold)
          .fontColor('#007DFF')
          .margin({ top: 80 })

        Text('记录美好瞬间')
          .fontSize(14)
          .fontColor(Color.Gray)
          .margin({ top: 10 })
      }
      .width('100%')
      .margin({ bottom: 60 })

      // 登录表单
      Column() {
        // 用户名输入框
        TextInput({ placeholder: '用户名 / 手机号', text: this.username })
          .width('85%')
          .height(50)
          .fontSize(16)
          .backgroundColor('#F5F5F5')
          .borderRadius(25)
          .padding({ left: 20 })
          .onChange((value: string) => {
            this.username = value;
            this.errorMsg = '';
          })

        // 密码输入框
        Row() {
          TextInput({ placeholder: '密码', text: this.password })
            .layoutWeight(1)
            .height(50)
            .fontSize(16)
            .backgroundColor('#F5F5F5')
            .borderRadius(25)
            .padding({ left: 20 })
            .type(this.showPassword ? InputType.Normal : InputType.Password)
            .onChange((value: string) => {
              this.password = value;
              this.errorMsg = '';
            })

          Button(this.showPassword ? '🙈' : '👁️')
            .width(50)
            .height(50)
            .backgroundColor(Color.Transparent)
            .fontSize(20)
            .onClick(() => {
              this.showPassword = !this.showPassword;
            })
        }
        .width('85%')
        .margin({ top: 15 })

        // 错误提示
        if (this.errorMsg) {
          Text(this.errorMsg)
            .fontSize(12)
            .fontColor(Color.Red)
            .width('85%')
            .margin({ top: 10 })
        }

        // 记住密码
        Row() {
          Row() {
            Checkbox()
              .width(18)
              .height(18)
            Text('记住密码')
              .fontSize(14)
              .fontColor(Color.Gray)
              .margin({ left: 5 })
          }
          Blank()
          Text('忘记密码？')
            .fontSize(14)
            .fontColor('#007DFF')
        }
        .width('85%')
        .margin({ top: 15 })

        // 登录按钮
        Button('登录')
          .width('85%')
          .height(50)
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .backgroundColor('#007DFF')
          .borderRadius(25)
          .margin({ top: 30 })
          .onClick(() => {
            if (this.username === 'sit' && this.password === 'sit') {
              this.isLoggedIn = true;
              promptAction.showToast({
                message: '登录成功！',
                duration: 1500
              });
            } else {
              this.errorMsg = '用户名或密码错误\n测试账号: test / 123456';
            }
          })

        // 注册提示
        Row() {
          Text('还没有账号？')
            .fontSize(14)
            .fontColor(Color.Gray)

          Text('立即注册')
            .fontSize(14)
            .fontColor('#007DFF')
            .fontWeight(FontWeight.Medium)
            .margin({ left: 5 })
            .onClick(() => {
              promptAction.showToast({
                message: '注册功能开发中',
                duration: 1500
              });
            })
        }
        .margin({ top: 30 })

        // 测试账号提示
        Text('测试账号: test / 123456')
          .fontSize(12)
          .fontColor('#999999')
          .margin({ top: 20 })
      }
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Color.White)
  }

  @Builder
  HomePage() {
    Column() {
      Text(`欢迎回来，${this.username}！`)
        .fontSize(28)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 100 })

      Text('登录成功！')
        .fontSize(16)
        .fontColor(Color.Gray)
        .margin({ top: 20 })

      Button('退出登录')
        .width('60%')
        .height(45)
        .fontSize(16)
        .backgroundColor('#FF6B6B')
        .borderRadius(25)
        .margin({ top: 50 })
        .onClick(() => {
          this.isLoggedIn = false;
          this.username = '';
          this.password = '';
        })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Color.White)
  }
}