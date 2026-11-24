// MainPage.ets - 无线AI智能打分相册
import { photoAccessHelper } from '@kit.MediaLibraryKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { promptAction } from '@kit.ArkUI';
import router from '@ohos.router';
import { databaseHelper, PhotoData } from '../common/DatabaseHelper';

// ==================== 全局状态初始化 ====================
function initGlobalState(): void {
  if (!AppStorage.has('isLoggedIn')) {
    AppStorage.setOrCreate('isLoggedIn', false);
  }
  if (!AppStorage.has('username')) {
    AppStorage.setOrCreate('username', '');
  }
  if (!AppStorage.has('selectedPhotos')) {
    AppStorage.setOrCreate('selectedPhotos', []);
  }
  if (!AppStorage.has('syncedPhotos')) {
    AppStorage.setOrCreate('syncedPhotos', []);
  }
  if (!AppStorage.has('isDeviceConnected')) {
    AppStorage.setOrCreate('isDeviceConnected', false);
  }
  if (!AppStorage.has('latestMemoryPhoto')) {
    AppStorage.setOrCreate('latestMemoryPhoto', '');
  }
  if (!AppStorage.has('photoScores')) {
    AppStorage.setOrCreate('photoScores', new Map<string, number>());
  }
}
initGlobalState();

// ==================== 登录页面 ====================
@Component
struct LoginPage {
  @State username: string = '';
  @State password: string = '';
  @State showPassword: boolean = false;
  @State errorMsg: string = '';
  private onLoginSuccess: () => void = () => {};

  build() {
    Column() {
      // Logo
      Column() {
        Text('📷')
          .fontSize(60)
          .margin({ bottom: 10 })
        Text('智绘相册')
          .fontSize(36)
          .fontWeight(FontWeight.Bold)
          .fontColor('#007DFF')
      }
      .margin({ top: 80, bottom: 40 })

      // 用户名输入
      TextInput({ placeholder: '用户名', text: this.username })
        .width('80%')
        .height(50)
        .fontSize(16)
        .backgroundColor('#F5F5F5')
        .borderRadius(25)
        .padding({ left: 20 })
        .onChange((value: string) => {
          this.username = value;
          this.errorMsg = '';
        })

      // 密码输入
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

        Button(this.showPassword ? '👁️' : '👁️‍🗨️')
          .width(50)
          .height(50)
          .backgroundColor(Color.Transparent)
          .fontSize(20)
          .onClick(() => {
            this.showPassword = !this.showPassword;
          })
      }
      .width('80%')
      .margin({ top: 15 })

      // 错误提示
      if (this.errorMsg) {
        Text(this.errorMsg)
          .fontSize(12)
          .fontColor(Color.Red)
          .width('80%')
          .margin({ top: 10 })
      }

      // 登录按钮
      Button('登录')
        .width('80%')
        .height(50)
        .fontSize(18)
        .fontWeight(FontWeight.Bold)
        .backgroundColor('#007DFF')
        .borderRadius(25)
        .margin({ top: 30 })
        .onClick(() => {
          if (this.username === 'sit' && this.password === 'sit') {
            AppStorage.set('isLoggedIn', true);
            AppStorage.set('username', this.username);
            promptAction.showToast({ message: '登录成功！', duration: 1500 });
            this.onLoginSuccess();
          } else {
            this.errorMsg = '用户名或密码错误\n测试账号: test / 123456';
          }
        })

      Text('测试账号: test / 123456')
        .fontSize(12)
        .fontColor('#999999')
        .margin({ top: 30 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Color.White)
  }
}

// ==================== 轮播图数据接口 ====================
interface SwiperItem {
  image: Resource;
  title: string;
  desc: string;
}

// ==================== 快捷功能组件 ====================
@Component
struct ShortcutItem {
  iconName: string = '';
  title: string = '';
  onItemClick: () => void = () => {};

  build() {
    Column() {
      Text(this.iconName)
        .fontSize(28)
        .width(60)
        .height(60)
        .textAlign(TextAlign.Center)
        .backgroundColor('#F0F0F0')
        .borderRadius(30)
        .padding({ top: 15 })
      Text(this.title)
        .fontSize(12)
        .fontColor(Color.Black)
        .margin({ top: 8 })
    }
    .onClick(() => this.onItemClick())
  }
}

// ==================== 往年今日弹窗组件 ====================
@Component
struct YearBeforeTodayDialog {
  @Prop yearPhotos: Array<string> = [];
  @Prop currentYear: number = 0;
  @Prop isLoading: boolean = true;
  private onClose: () => void = () => {};
  private onSelectPhoto: (photo: string) => void = () => {};
  private onAddPhotos: (photos: Array<string>) => void = () => {};
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  build() {
    Column() {
      // 标题栏
      Row() {
        Text(`往年今日 (${this.currentYear}年)`)
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .layoutWeight(1)
        Button('✕')
          .fontSize(20)
          .backgroundColor(Color.Transparent)
          .fontColor('#666666')
          .onClick(() => this.onClose())
      }
      .width('100%')
      .padding(15)

      if (this.isLoading) {
        Column() {
          Text('🔄')
            .fontSize(40)
            .margin({ top: 50 })
          Text('正在加载往年今日照片...')
            .fontSize(14)
            .fontColor('#999999')
            .margin({ top: 10 })
        }
        .width('100%')
        .height(300)
        .justifyContent(FlexAlign.Center)
      } else if (this.yearPhotos.length === 0) {
        Column() {
          Text('📷')
            .fontSize(40)
            .margin({ top: 50 })
          Text('暂无往年今日照片')
            .fontSize(14)
            .fontColor('#999999')
            .margin({ top: 10 })
          Button('选择照片添加')
            .width('60%')
            .height(40)
            .fontSize(14)
            .backgroundColor('#007DFF')
            .borderRadius(20)
            .margin({ top: 20 })
            .onClick(() => this.selectYearPhotos())
        }
        .width('100%')
        .height(300)
        .justifyContent(FlexAlign.Center)
      } else {
        // 照片网格
        Grid() {
          ForEach(this.yearPhotos, (photo: string, index: number) => {
            GridItem() {
              Column() {
                Image(photo)
                  .width(100)
                  .height(100)
                  .borderRadius(8)
                  .objectFit(ImageFit.Cover)
                  .onClick(() => this.onSelectPhoto(photo))
              }
              .padding(5)
            }
          })
        }
        .columnsTemplate('1fr 1fr 1fr')
        .width('100%')
        .height(250)
        .padding(10)
      }

      // 操作按钮
      Row() {
        Button('添加照片')
          .width('45%')
          .height(40)
          .fontSize(14)
          .backgroundColor('#4ECDC4')
          .borderRadius(20)
          .onClick(() => this.selectYearPhotos())
        Button('关闭')
          .width('45%')
          .height(40)
          .fontSize(14)
          .backgroundColor('#F0F0F0')
          .fontColor('#666666')
          .borderRadius(20)
          .onClick(() => this.onClose())
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceAround)
      .padding(15)
    }
    .width('90%')
    .backgroundColor(Color.White)
    .borderRadius(15)
    .shadow({ radius: 20, color: '#00000020', offsetX: 0, offsetY: 5 })
  }

  private async selectYearPhotos(): Promise<void> {
    console.info('点击了添加照片按钮');

    // 等待数据库初始化（最多等待3秒）
    let waitCount = 0;
    const maxWait = 6;

    while (!databaseHelper.isInitialized() && waitCount < maxWait) {
      console.info(`等待数据库初始化... 第${waitCount + 1}次`);
      await this.sleep(500);
      waitCount++;
    }

    if (!databaseHelper.isInitialized()) {
      console.error('数据库未初始化');
      promptAction.showToast({ message: '数据库未初始化，请重启应用', duration: 2000 });
      return;
    }

    try {
      let photoSelectOptions = new photoAccessHelper.PhotoSelectOptions();
      photoSelectOptions.MIMEType = photoAccessHelper.PhotoViewMIMETypes.IMAGE_TYPE;
      photoSelectOptions.maxSelectNumber = 9;

      console.info('创建PhotoPicker实例');
      let photoPicker = new photoAccessHelper.PhotoViewPicker();

      console.info('开始调用PhotoPicker.select');
      photoPicker.select(photoSelectOptions).then(async (photoSelectResult: photoAccessHelper.PhotoSelectResult) => {
        console.info(`PhotoPicker返回成功，选择了 ${photoSelectResult.photoUris.length} 张照片`);
        if (photoSelectResult.photoUris.length > 0) {
          // 保存到数据库，标记为往年回忆
          const currentTime = Date.now();
          const today = new Date();

          console.info(`开始保存 ${photoSelectResult.photoUris.length} 张照片到数据库`);

          for (const uri of photoSelectResult.photoUris) {
            const photoData: PhotoData = {
              uri: uri,
              create_time: currentTime,
              modify_time: currentTime,
              year: today.getFullYear() - 1, // 往年的年份
              month: today.getMonth() + 1,
              day: today.getDate(),
              is_selected: 0,
              is_year_memory: 1,
              score: 0
            };
            try {
              await databaseHelper.insertPhoto(photoData);
              console.info(`照片保存成功: ${uri}`);
            } catch (err) {
              console.error(`照片保存失败: ${JSON.stringify(err)}`);
            }
          }

          // 调用回调函数通知父组件更新照片列表
          this.onAddPhotos(photoSelectResult.photoUris);
          promptAction.showToast({ message: `已添加 ${photoSelectResult.photoUris.length} 张照片`, duration: 1500 });
        } else {
          console.info('用户没有选择任何照片');
        }
      }).catch((err: BusinessError) => {
        console.error(`PhotoPicker 失败: ${err.code}, ${err.message}`);
        promptAction.showToast({ message: `选择照片失败: ${err.message}`, duration: 2000 });
      });
    } catch (error) {
      const err: BusinessError = error as BusinessError;
      console.error(`调用 PhotoPicker 异常: ${err.code}, ${err.message}`);
      promptAction.showToast({ message: `异常: ${err.message}`, duration: 2000 });
    }
  }
}

// ==================== 主页 ====================
@Component
struct HomePage {
  @StorageLink('selectedPhotos') selectedPhotos: Array<string> = [];
  @StorageLink('syncedPhotos') syncedPhotos: Array<string> = [];
  @StorageLink('isDeviceConnected') isDeviceConnected: boolean = false;
  @StorageLink('username') username: string = '';
  @StorageLink('latestMemoryPhoto') latestMemoryPhoto: string = '';
  @State showYearBeforeTodayDialog: boolean = false;
  @State yearBeforeTodayPhotos: Array<string> = [];
  @State yearBeforeTodayYear: number = 0;
  @State isLoading: boolean = false;

  @State swiperItems: Array<SwiperItem> = [
    { image: $r('app.media.photo1'), title: '美好回忆', desc: '点击查看精彩瞬间' },
    { image: $r('app.media.photo2'), title: '智能相册', desc: 'AI自动分类打分' },
    { image: $r('app.media.photo3'), title: '水墨屏联动', desc: '无线传输至墨水屏' }
  ];

  private swiperController: SwiperController = new SwiperController();

  // 组件即将显示时加载数据库数据
  aboutToAppear(): void {
    this.loadDataFromDatabase();
  }

  // 从数据库加载数据
  private async loadDataFromDatabase(): Promise<void> {
    try {
      // 等待数据库初始化（最多等待3秒）
      let waitCount = 0;
      const maxWait = 6;

      while (!databaseHelper.isInitialized() && waitCount < maxWait) {
        console.info(`等待数据库初始化... 第${waitCount + 1}次`);
        await this.sleep(500);
        waitCount++;
      }

      if (!databaseHelper.isInitialized()) {
        console.warn('数据库未初始化，加载默认数据');
        return;
      }

      console.info('数据库已初始化，开始加载数据');

      // 加载最新回忆
      const latestMemory = await databaseHelper.queryLatestMemory();
      if (latestMemory) {
        this.latestMemoryPhoto = latestMemory.uri;
        console.info(`加载最新回忆: ${latestMemory.uri}`);
      }

      // 加载已选照片
      const selectedPhotos = await databaseHelper.querySelectedPhotos();
      if (selectedPhotos.length > 0) {
        AppStorage.set('selectedPhotos', selectedPhotos.map((p: PhotoData) => p.uri));
        console.info(`加载了 ${selectedPhotos.length} 张已选照片`);
      }

      console.info('从数据库加载数据成功');
    } catch (error) {
      console.error(`从数据库加载数据失败: ${JSON.stringify(error)}`);
    }
  }

  // 睡眠函数
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  build() {
    Stack() {
      Scroll() {
        Column() {
          // 欢迎语和设备状态
          Row() {
            Text('欢迎，SITer！')
              .fontSize(20)
              .fontWeight(FontWeight.Bold)
            Blank()
            if (this.isDeviceConnected) {
              Text('✅ 设备已连接')
                .fontSize(12)
                .fontColor('#4ECDC4')
            }
          }
          .width('100%')
          .padding({ left: 20, right: 20, bottom: 10 })

          // 轮播图
          Swiper(this.swiperController) {
            ForEach(this.swiperItems, (item: SwiperItem, index: number) => {
              Stack({ alignContent: Alignment.BottomStart }) {
                Image(item.image)
                  .width('100%')
                  .height('100%')
                  .objectFit(ImageFit.Cover)
                  .borderRadius(12)
                Column() {
                  Text(item.title)
                    .fontSize(24)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(Color.White)
                  Text(item.desc)
                    .fontSize(14)
                    .fontColor(Color.White)
                    .opacity(0.9)
                }
                .margin({ left: 16, bottom: 16 })
              }
              .width('100%')
              .height(200)
              .borderRadius(12)
              .onClick(() => {
                console.info(`点击了第 ${index + 1} 张轮播图: ${item.title}`);
              })
            })
          }
          .width('100%')
          .height(200)
          .autoPlay(true)
          .interval(4000)
          .loop(true)
          .indicator(new DotIndicator().color(Color.Gray).selectedColor(Color.White))
          .margin({ bottom: 20 })

          // 快捷功能按钮
          Row() {
            ShortcutItem({
              iconName: '📅',
              title: '往年今日',
              onItemClick: () => this.showYearBeforeToday()
            })
            ShortcutItem({
              iconName: '🔍',
              title: '筛选照片',
              onItemClick: () => this.selectPhotos()
            })
            ShortcutItem({
              iconName: this.isDeviceConnected ? '📡' : '🏆',
              title: this.isDeviceConnected ? '已连接' : '他日最佳',
              onItemClick: () => this.showBestPhotoBefore()
            })
          }
          .width('100%')
          .justifyContent(FlexAlign.SpaceAround)
          .padding({ left: 20, right: 20 })

          // 已选照片提示
          if (this.selectedPhotos.length > 0) {
            Column() {
              Text(`已选择 ${this.selectedPhotos.length} 张照片`)
                .fontSize(14)
                .fontColor('#007DFF')
                .margin({ top: 20 })
              Button('同步到水墨屏')
                .width('80%')
                .height(40)
                .fontSize(16)
                .backgroundColor('#007DFF')
                .borderRadius(20)
                .margin({ top: 10 })
                .onClick(() => this.syncToDevice())
            }
            .width('100%')
          }

          // 最新回忆（单张照片，点击可连接本地相册）
          Text('今日照片')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .width('100%')
            .padding({ left: 20, top: 20, bottom: 10 })

          Column() {
            Image('https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/best-photo/%E7%85%A7%E7%89%87%20%2873%29.jpg')
              .width('90%')
              .aspectRatio(0.75)
              .borderRadius(12)
              .objectFit(ImageFit.Contain)
          }
          .width('100%')
          .justifyContent(FlexAlign.Center)
          .padding({ bottom: 20 })
        }
        .width('100%')
        .padding({ top: 10 })
      }
      .width('100%')
      .height('100%')
      .scrollBar(BarState.Off)

      // 往年今日弹窗
      if (this.showYearBeforeTodayDialog) {
        Column() {
          Blank()
          YearBeforeTodayDialog({
            yearPhotos: this.yearBeforeTodayPhotos,
            currentYear: this.yearBeforeTodayYear,
            isLoading: this.isLoading,
            onClose: () => {
              this.showYearBeforeTodayDialog = false;
            },
            onSelectPhoto: (photo: string): void => {
              AppStorage.set('latestMemoryPhoto', photo);
              this.showYearBeforeTodayDialog = false;
              promptAction.showToast({ message: '已设置为今日照片', duration: 1500 });
            },
            onAddPhotos: (photos: Array<string>): void => {
              // 更新父组件的照片列表
              this.yearBeforeTodayPhotos = [...this.yearBeforeTodayPhotos, ...photos];
            }
          })
          Blank()
        }
        .width('100%')
        .height('100%')
        .backgroundColor('#00000080')
        .onClick(() => {
          this.showYearBeforeTodayDialog = false;
        })
      }
    }
    .width('100%')
    .height('100%')
  }

  // 往年今日功能 - 跳转到 ThisDayBefore 页面
  private showYearBeforeToday(): void {
    try {
      router.pushUrl({ url: 'pages/ThisDayBefore' });
    } catch (err) {
      console.error('跳转失败:', JSON.stringify(err));
      promptAction.showToast({ message: '跳转失败，请重试', duration: 2000 });
    }
  }

  // 选择照片 - 跳转到照片筛选页面
  private selectPhotos(): void {
    try {
      router.pushUrl({ url: 'pages/Photos' });
    } catch (err) {
      console.error('跳转失败:', JSON.stringify(err));
      promptAction.showToast({ message: '跳转失败，请重试', duration: 2000 });
    }
  }

  // 他日最佳 - 跳转到 BestPhotoBefore 页面
  private showBestPhotoBefore(): void {
    try {
      router.pushUrl({ url: 'pages/BestPhotoBefore' });
    } catch (err) {
      console.error('跳转失败:', JSON.stringify(err));
      promptAction.showToast({ message: '跳转失败，请重试', duration: 2000 });
    }
  }

  // 选择最新回忆照片
  private selectLatestMemory(): void {
    console.info('点击了最新回忆，准备打开照片选择器');
    try {
      let photoSelectOptions = new photoAccessHelper.PhotoSelectOptions();
      photoSelectOptions.MIMEType = photoAccessHelper.PhotoViewMIMETypes.IMAGE_TYPE;
      photoSelectOptions.maxSelectNumber = 1;

      console.info('创建PhotoPicker实例');
      let photoPicker = new photoAccessHelper.PhotoViewPicker();

      console.info('开始调用PhotoPicker.select');
      photoPicker.select(photoSelectOptions).then(async (photoSelectResult: photoAccessHelper.PhotoSelectResult) => {
        console.info(`PhotoPicker返回成功，选择了 ${photoSelectResult.photoUris.length} 张照片`);
        if (photoSelectResult.photoUris.length > 0) {
          const uri = photoSelectResult.photoUris[0];
          console.info(`选择的照片URI: ${uri}`);

          // 保存到数据库
          const currentTime = Date.now();
          const today = new Date();
          const photoData: PhotoData = {
            uri: uri,
            create_time: currentTime,
            modify_time: currentTime,
            year: today.getFullYear(),
            month: today.getMonth() + 1,
            day: today.getDate(),
            is_selected: 0,
            is_year_memory: 1,
            score: 0
          };
          await databaseHelper.insertPhoto(photoData);

          // 更新内存中的数据
          AppStorage.set('latestMemoryPhoto', uri);
          promptAction.showToast({ message: '已更新今日照片', duration: 1500 });
        }
      }).catch((err: BusinessError) => {
        console.error(`PhotoPicker 失败: ${err.code}, ${err.message}`);
        promptAction.showToast({ message: `选择照片失败: ${err.message}`, duration: 2000 });
      });
    } catch (error) {
      const err: BusinessError = error as BusinessError;
      console.error(`调用 PhotoPicker 异常: ${err.code}, ${err.message}`);
      promptAction.showToast({ message: `异常: ${err.message}`, duration: 2000 });
    }
  }

  // 同步到设备
  private syncToDevice(): void {
    if (!this.isDeviceConnected) {
      promptAction.showToast({ message: '请先连接水墨屏设备', duration: 2000 });
      return;
    }
    if (this.selectedPhotos.length === 0) {
      promptAction.showToast({ message: '请先选择照片', duration: 2000 });
      return;
    }
    promptAction.showToast({ message: `正在同步 ${this.selectedPhotos.length} 张照片...`, duration: 1500 });
    setTimeout((): void => {
      let synced = AppStorage.get<Array<string>>('syncedPhotos') || [];
      AppStorage.set('syncedPhotos', [...synced, ...this.selectedPhotos]);
      AppStorage.set('selectedPhotos', []);
      promptAction.showToast({ message: '同步成功！', duration: 1500 });
    }, 1000);
  }

  // 连接设备
  private connectToDevice(): void {
    if (this.isDeviceConnected) {
      promptAction.showToast({ message: '设备已连接', duration: 1500 });
      return;
    }
    promptAction.showToast({ message: '正在连接水墨屏设备...', duration: 1500 });
    setTimeout((): void => {
      AppStorage.set('isDeviceConnected', true);
      promptAction.showToast({ message: '设备连接成功！', duration: 1500 });
    }, 1000);
  }
}

// ==================== 设置项组件 ====================
@Component
struct SettingsItem {
  icon: string = '';
  title: string = '';
  desc: string = '';
  onItemClick: () => void = () => {};

  build() {
    Row() {
      Text(this.icon)
        .fontSize(24)
        .width(40)
      Column() {
        Text(this.title)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
        if (this.desc) {
          Text(this.desc)
            .fontSize(12)
            .fontColor(Color.Gray)
        }
      }
      .alignItems(HorizontalAlign.Start)
      .margin({ left: 10 })
      .layoutWeight(1)
      Image($r('sys.symbol.chevron_right'))
        .width(16)
        .height(16)
        .opacity(0.4)
    }
    .width('100%')
    .height(56)
    .padding({ left: 15, right: 15 })
    .onClick(() => this.onItemClick())
  }
}

// ==================== AI打分页面 ====================
@Component
struct AIScorePage {
  @StorageLink('selectedPhotos') selectedPhotos: Array<string> = [];
  @StorageLink('photoScores') photoScores: Map<string, number> = new Map();
  @State currentPhoto: string = '';
  @State currentScore: number = 0;
  @State isScoring: boolean = false;
  private onBack: () => void = () => {};

  build() {
    Column() {
      // 标题栏
      Row() {
        Button('← 返回')
          .fontSize(16)
          .backgroundColor(Color.Transparent)
          .fontColor('#007DFF')
          .onClick(() => this.onBack())
        Text('AI智能打分')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .layoutWeight(1)
          .textAlign(TextAlign.Center)
        Text('    ')
          .fontSize(16)
          .width(60)
      }
      .width('100%')
      .height(50)
      .padding({ left: 10, right: 10 })

      // 选择照片按钮
      Button('选择照片进行打分')
        .width('80%')
        .height(40)
        .fontSize(16)
        .backgroundColor('#007DFF')
        .borderRadius(20)
        .margin({ top: 20 })
        .onClick(() => this.selectPhotoForScore())

      // 当前照片展示
      if (this.currentPhoto) {
        Column() {
          Image(this.currentPhoto)
            .width('80%')
            .height(200)
            .borderRadius(12)
            .objectFit(ImageFit.Cover)
            .margin({ top: 20 })

          // 打分结果
          if (this.isScoring) {
            Row() {
              Text('AI正在分析...')
                .fontSize(16)
                .fontColor('#999999')
            }
            .margin({ top: 20 })
          } else if (this.currentScore > 0) {
            Column() {
              Text(`AI评分: ${this.currentScore}分`)
                .fontSize(24)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.getScoreColor(this.currentScore))
              Text(this.getScoreComment(this.currentScore))
                .fontSize(14)
                .fontColor('#666666')
                .margin({ top: 10 })
            }
            .margin({ top: 20 })
          }
        }
      }

      // 已打分照片列表
      if (this.selectedPhotos.length > 0) {
        Text('已打分照片')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .margin({ top: 30, bottom: 10 })
        List() {
          ForEach(this.selectedPhotos, (photo: string) => {
            ListItem() {
              Row() {
                Image(photo)
                  .width(60)
                  .height(60)
                  .borderRadius(8)
                  .objectFit(ImageFit.Cover)
                Text(`评分: ${this.photoScores.get(photo) || 0}分`)
                  .fontSize(14)
                  .margin({ left: 15 })
                  .layoutWeight(1)
                Button('重新打分')
                  .fontSize(12)
                  .height(30)
                  .backgroundColor('#007DFF')
                  .onClick(() => {
                    this.currentPhoto = photo;
                    this.performAIScore();
                  })
              }
              .width('100%')
              .padding(10)
            }
          })
        }
        .width('90%')
        .height(200)
        .margin({ top: 10 })
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Color.White)
  }

  private selectPhotoForScore(): void {
    try {
      let photoSelectOptions = new photoAccessHelper.PhotoSelectOptions();
      photoSelectOptions.MIMEType = photoAccessHelper.PhotoViewMIMETypes.IMAGE_TYPE;
      photoSelectOptions.maxSelectNumber = 1;

      let photoPicker = new photoAccessHelper.PhotoViewPicker();
      photoPicker.select(photoSelectOptions).then((photoSelectResult: photoAccessHelper.PhotoSelectResult) => {
        if (photoSelectResult.photoUris.length > 0) {
          this.currentPhoto = photoSelectResult.photoUris[0];
          this.performAIScore();
        }
      }).catch((err: BusinessError) => {
        console.error(`PhotoPicker 失败: ${err.code}, ${err.message}`);
      });
    } catch (error) {
      const err: BusinessError = error as BusinessError;
      console.error(`调用 PhotoPicker 异常: ${err.code}, ${err.message}`);
    }
  }

  private performAIScore(): void {
    this.isScoring = true;
    this.currentScore = 0;
    // 模拟AI打分过程
    setTimeout((): void => {
      this.currentScore = Math.floor(Math.random() * 40) + 60; // 60-100分
      this.isScoring = false;
      // 保存评分
      // ✅ 明确指定类型
      let scores: Map<string, number> = AppStorage.get<Map<string, number>>('photoScores') || new Map();
      scores.set(this.currentPhoto, this.currentScore);
      AppStorage.set('photoScores', scores);
      // 添加到已选照片列表
      let photos = AppStorage.get<Array<string>>('selectedPhotos') || [];
      if (!photos.includes(this.currentPhoto)) {
        AppStorage.set('selectedPhotos', [...photos, this.currentPhoto]);
      }
      promptAction.showToast({ message: `AI评分完成: ${this.currentScore}分`, duration: 1500 });
    }, 2000);
  }

  private getScoreColor(score: number): string {
    if (score >= 90) return '#4CAF50';
    if (score >= 80) return '#8BC34A';
    if (score >= 70) return '#FFC107';
    return '#FF9800';
  }

  private getScoreComment(score: number): string {
    if (score >= 90) return '优秀！构图精美，色彩和谐';
    if (score >= 80) return '良好！画面清晰，主题明确';
    if (score >= 70) return '中等！可以尝试调整角度';
    return '一般！建议重新拍摄';
  }
}

// ==================== 我的页面 ====================
@Component
struct ProfilePage {
  @StorageLink('username') username: string = '';
  @StorageLink('selectedPhotos') selectedPhotos: Array<string> = [];
  @StorageLink('syncedPhotos') syncedPhotos: Array<string> = [];
  @StorageLink('isDeviceConnected') isDeviceConnected: boolean = false;
  @StorageLink('isLoggedIn') isLoggedIn: boolean = false;
  @State showAIScorePage: boolean = false;
  private onLogout: () => void = () => {};

  build() {
    if (this.showAIScorePage) {
      AIScorePage({
        onBack: () => {
          this.showAIScorePage = false;
        }
      })
    } else {
      Column() {
        // 用户信息
        Row() {
          Circle()
            .width(60)
            .height(60)
            .fill('#B0C4DE')
          Text(this.username ? this.username.charAt(0).toUpperCase() : 'AI')
            .fontSize(24)
            .fontColor(Color.White)
          Column() {
            Text(this.username || '智绘相册')
              .fontSize(18)
              .fontWeight(FontWeight.Bold)
            Text('无线 AI 智能打分相册')
              .fontSize(12)
              .fontColor(Color.Gray)
          }
          .alignItems(HorizontalAlign.Start)
          .margin({ left: 15 })
          Blank()
          Button('退出登录')
            .fontSize(14)
            .height(30)
            .backgroundColor('#FF6B6B')
            .borderRadius(15)
            .onClick(() => {
              AppStorage.set('isLoggedIn', false);
              AppStorage.set('username', '');
              AppStorage.set('selectedPhotos', []);
              AppStorage.set('syncedPhotos', []);
              AppStorage.set('isDeviceConnected', false);
              AppStorage.set('latestMemoryPhoto', '');
              promptAction.showToast({ message: '已退出登录', duration: 1500 });
              this.onLogout();
            })
        }
        .width('100%')
        .padding(15)
        .backgroundColor('#F8F8F8')

        // 功能列表
        List() {
          // 相册管理（可连接本地相册）
          ListItem() {
            SettingsItem({
              icon: '🖼️',
              title: '相册管理',
              desc: `已同步 ${this.syncedPhotos.length} 张图片`,
              onItemClick: () => this.openLocalGallery()
            })
          }
          // 设备连接
          ListItem() {
            SettingsItem({
              icon: '📡',
              title: '设备连接',
              desc: this.isDeviceConnected ? '已连接' : '未连接',
              onItemClick: () => this.connectDevice()
            })
          }
          // AI打分
          ListItem() {
            SettingsItem({
              icon: '⭐',
              title: 'AI打分',
              desc: '智能照片评分系统',
              onItemClick: () => {
                this.showAIScorePage = true;
              }
            })
          }
          // 设备版本
          ListItem() {
            SettingsItem({
              icon: 'ℹ️',
              title: '设备版本',
              desc: '固件版本 v1.0.0',
              onItemClick: () => {
                promptAction.showToast({
                  message: '智绘相册 v1.0.0\n无线AI智能打分相册',
                  duration: 2000
                });
              }
            })
          }
        }
        .width('100%')
        .height('100%')
        .divider({ strokeWidth: 1, color: '#EEEEEE', startMargin: 60, endMargin: 15 })
        .scrollBar(BarState.Off)
      }
      .width('100%')
      .height('100%')
      .backgroundColor(Color.White)
    }
  }

  // 打开本地相册
  private openLocalGallery(): void {
    try {
      let photoSelectOptions = new photoAccessHelper.PhotoSelectOptions();
      photoSelectOptions.MIMEType = photoAccessHelper.PhotoViewMIMETypes.IMAGE_TYPE;
      photoSelectOptions.maxSelectNumber = 20;

      let photoPicker = new photoAccessHelper.PhotoViewPicker();
      photoPicker.select(photoSelectOptions).then((photoSelectResult: photoAccessHelper.PhotoSelectResult) => {
        if (photoSelectResult.photoUris.length > 0) {
          let currentPhotos: Array<string> = AppStorage.get<Array<string>>('syncedPhotos') || [];
          AppStorage.set('syncedPhotos', [...currentPhotos, ...photoSelectResult.photoUris]);
          promptAction.showToast({
            message: `已从本地相册添加 ${photoSelectResult.photoUris.length} 张照片`,
            duration: 2000
          });
        }
      }).catch((err: BusinessError) => {
        console.error(`PhotoPicker 失败: ${err.code}, ${err.message}`);
      });
    } catch (error) {
      const err: BusinessError = error as BusinessError;
      console.error(`调用 PhotoPicker 异常: ${err.code}, ${err.message}`);
    }
  }

  // 连接设备
  private connectDevice(): void {
    if (this.isDeviceConnected) {
      promptAction.showToast({ message: '设备已连接', duration: 1500 });
      return;
    }
    promptAction.showToast({ message: '正在连接水墨屏设备...', duration: 1500 });
    setTimeout((): void => {
      AppStorage.set('isDeviceConnected', true);
      promptAction.showToast({ message: '设备连接成功！', duration: 1500 });
    }, 1000);
  }
}

// ==================== 主入口 ====================
@Entry
@Component
struct MainPage {
  @StorageLink('isLoggedIn') isLoggedIn: boolean = false;
  @State currentTabIndex: number = 0;

  build() {
    if (!this.isLoggedIn) {
      LoginPage({
        onLoginSuccess: () => {
          this.currentTabIndex = 0;
        }
      })
    } else {
      Tabs({ barPosition: BarPosition.End, index: this.currentTabIndex }) {
        TabContent() {
          HomePage()
        }
        .tabBar(this.TabBuilder('首页', '🏠', 0))

        TabContent() {
          ProfilePage({
            onLogout: () => {
              this.isLoggedIn = false;
            }
          })
        }
        .tabBar(this.TabBuilder('我的', '👤', 1))
      }
      .width('100%')
      .height('100%')
      .backgroundColor('#F5F5F5')
      .onChange((index: number) => {
        this.currentTabIndex = index;
      })
      .barHeight(60)
      .barMode(BarMode.Fixed)
    }
  }

  @Builder
  TabBuilder(title: string, icon: string, index: number) {
    Column() {
      Text(icon)
        .fontSize(24)
        .fontColor(this.currentTabIndex === index ? '#007DFF' : '#999999')
      Text(title)
        .fontSize(12)
        .fontColor(this.currentTabIndex === index ? '#007DFF' : '#999999')
        .margin({ top: 4 })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}